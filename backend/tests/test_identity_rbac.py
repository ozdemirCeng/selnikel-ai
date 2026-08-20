"""
Comprehensive Identity, RBAC & OIDC External Mapping Security Test Suite
Validates:
1. User domain model permission evaluation & wildcard permissions
2. Raw email token spoofing protection (rejected in all modes)
3. Development mode authentication (X-Dev-User / dev-token)
4. OIDC mode JWT verification (valid, expired, tampered, zero-privilege unmapped)
5. Zero Seed Escalation in OIDC mode (admin email without DB mapping gets ZERO privileges)
6. Database error fail-closed 503 behavior in OIDC mode
7. External identity table resolution (issuer + subject -> internal user)
8. BFF mode HMAC session cookie verification
9. Startup configuration fail-fast gates in production
"""
import time
import json
import hmac
import hashlib
import pytest
import jwt
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.dependencies import get_db, resolve_user_from_db_or_seed
from app.core.config import settings
from app.domain.identity.models import User, Role, Permission
from app.db.models.identity import (
    UserModel,
    RoleModel,
    PermissionModel,
    UserRoleModel,
    RolePermissionModel,
    DepartmentModel,
    DepartmentMembershipModel,
    UserExternalIdentityModel,
)

@pytest.fixture(autouse=True)
def reset_settings_and_db():
    orig_mode = settings.AUTH_MODE
    orig_jwt_sec = settings.JWT_SECRET_KEY
    orig_iss = settings.OIDC_ISSUER
    orig_aud = settings.OIDC_AUDIENCE
    orig_cid = settings.OIDC_CLIENT_ID
    orig_sess_sec = settings.SESSION_SECRET_KEY
    orig_env = settings.ENVIRONMENT

    # Default mock DB returning empty to avoid live connection
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[])))))
    
    async def mock_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db

    yield

    app.dependency_overrides.clear()
    settings.AUTH_MODE = orig_mode
    settings.JWT_SECRET_KEY = orig_jwt_sec
    settings.OIDC_ISSUER = orig_iss
    settings.OIDC_AUDIENCE = orig_aud
    settings.OIDC_CLIENT_ID = orig_cid
    settings.SESSION_SECRET_KEY = orig_sess_sec
    settings.ENVIRONMENT = orig_env


def test_user_domain_permission_logic():
    admin = User(
        id="usr-001",
        email="admin@selnikel.com.tr",
        display_name="Admin",
        status="active",
        department_ids=["dept-management"],
        role_codes=["super_admin"],
        permissions=["*"],
    )
    assert admin.has_permission("document.read") is True
    assert admin.has_permission("anything.random") is True
    assert admin.can_access_department("dept-engineering") is True
    assert admin.has_department_access("dept-engineering") is True

    engineer = User(
        id="usr-002",
        email="engineer@selnikel.com.tr",
        display_name="Engineer",
        status="active",
        department_ids=["dept-engineering"],
        role_codes=["engineer"],
        permissions=["document.read", "document.upload"],
    )
    assert engineer.has_permission("document.read") is True
    assert engineer.has_permission("admin.users.write") is False
    assert engineer.can_access_department("dept-engineering") is True
    assert engineer.can_access_department("dept-management") is False


@pytest.mark.asyncio
async def test_raw_email_token_rejected_in_all_modes():
    """Verify that using a raw email string as a Bearer token is strictly rejected with 401."""
    for mode in ["development", "oidc", "bff"]:
        settings.AUTH_MODE = mode
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/documents", headers={"Authorization": "Bearer admin@selnikel.com.tr"})
            assert res.status_code == 401


@pytest.mark.asyncio
async def test_auth_mode_development():
    settings.AUTH_MODE = "development"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Unauthenticated -> 401
        res_unauth = await ac.get("/api/v1/documents")
        assert res_unauth.status_code == 401

        # 2. Authenticated via X-Dev-User
        res_dev_header = await ac.get("/api/v1/documents", headers={"X-Dev-User": "engineer@selnikel.com.tr"})
        assert res_dev_header.status_code == 200

        # 3. Authenticated via dev-token- Bearer
        res_dev_token = await ac.get("/api/v1/documents", headers={"Authorization": "Bearer dev-token-engineer@selnikel.com.tr"})
        assert res_dev_token.status_code == 200


@pytest.mark.asyncio
async def test_auth_mode_oidc_jwt_verification():
    settings.AUTH_MODE = "oidc"
    settings.JWT_SECRET_KEY = "test-oidc-secret-key-32-chars-long!"
    settings.OIDC_ISSUER = "https://auth.selnikel.com.tr"
    settings.OIDC_AUDIENCE = "selnikel-ai"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Missing Authorization -> 401
        res_no_auth = await ac.get("/api/v1/documents")
        assert res_no_auth.status_code == 401

        # 2. Valid JWT for an unmapped external user -> ZERO privileges -> 403 on protected endpoint
        unmapped_payload = {
            "sub": "ext-user-999",
            "email": "external_vendor@contractor.com",
            "iss": "https://auth.selnikel.com.tr",
            "aud": "selnikel-ai",
            "exp": time.time() + 3600,
        }
        unmapped_jwt = jwt.encode(unmapped_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        res_unmapped = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {unmapped_jwt}"})
        assert res_unmapped.status_code == 403

        # 3. Expired JWT -> 401
        expired_payload = {**unmapped_payload, "exp": time.time() - 60}
        expired_jwt = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        res_exp = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {expired_jwt}"})
        assert res_exp.status_code == 401

        # 4. Tampered signature -> 401
        tampered_jwt = jwt.encode(unmapped_payload, "wrong-secret-key", algorithm="HS256")
        res_tamp = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {tampered_jwt}"})
        assert res_tamp.status_code == 401


@pytest.mark.asyncio
async def test_oidc_mode_no_seed_escalation_in_production():
    """
    CRITICAL SECURITY TEST:
    In OIDC mode, an external token having email='admin@selnikel.com.tr' but NOT mapped in DB
    MUST NOT be granted super_admin privileges through SEED_USERS fallback.
    """
    settings.AUTH_MODE = "oidc"
    settings.JWT_SECRET_KEY = "test-oidc-secret-key-32-chars-long!"
    settings.OIDC_ISSUER = "https://auth.selnikel.com.tr"
    settings.OIDC_AUDIENCE = "selnikel-ai"

    # Token claiming admin email without DB mapping
    attacker_payload = {
        "sub": "ext-attacker-id",
        "email": "admin@selnikel.com.tr",  # Known seed admin email
        "iss": "https://auth.selnikel.com.tr",
        "aud": "selnikel-ai",
        "exp": time.time() + 3600,
    }
    attacker_jwt = jwt.encode(attacker_payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    # DB returns None (unmapped)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[])))))
    
    async def mock_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = mock_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Accessing protected action requiring permissions must return 403 Forbidden, NOT 200!
        res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {attacker_jwt}"})
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_oidc_mode_db_outage_fail_closed_503():
    """
    Verify that in OIDC mode, if the database encounters an unhandled exception,
    the system FAILS CLOSED with HTTP 503 rather than falling back to unauthenticated/seed access.
    """
    settings.AUTH_MODE = "oidc"
    settings.JWT_SECRET_KEY = "test-oidc-secret-key-32-chars-long!"
    settings.OIDC_ISSUER = "https://auth.selnikel.com.tr"
    settings.OIDC_AUDIENCE = "selnikel-ai"

    payload = {
        "sub": "usr-test-503",
        "email": "engineer@selnikel.com.tr",
        "iss": "https://auth.selnikel.com.tr",
        "aud": "selnikel-ai",
        "exp": time.time() + 3600,
    }
    valid_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    # Mock DB raising operational error
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Database connection pool exhausted / Timeout"))
    
    async def mock_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = mock_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert res.status_code == 503
        assert "Fail-closed" in res.json()["detail"] or "erişilemedi" in res.json()["detail"]


@pytest.mark.asyncio
async def test_oidc_external_identity_table_resolution():
    """
    Verify that user_external_identities table (issuer + subject + tenant_id)
    correctly resolves internal UserModel, roles, and permissions.
    """
    settings.AUTH_MODE = "oidc"
    mock_db = AsyncMock()

    # Mock UserExternalIdentity
    mock_ext_ident = MagicMock(spec=UserExternalIdentityModel)
    mock_ext_ident.user_id = "internal-usr-uuid-001"

    # Mock UserModel
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = "internal-usr-uuid-001"
    mock_user.email = "mapped_engineer@selnikel.com.tr"
    mock_user.display_name = "Mapped Engineer"
    mock_user.status = "active"

    res1 = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_ext_ident))))
    res2 = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_user))))
    res3 = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["engineer"]))))
    res4 = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["document.read", "document.upload"]))))
    res5 = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["dept-engineering"]))))

    mock_db.execute = AsyncMock(side_effect=[res1, res2, res3, res4, res5])

    user = await resolve_user_from_db_or_seed(
        sub="ext-sub-azure-12345",
        email="mapped_engineer@selnikel.com.tr",
        display_name="Mapped Engineer",
        issuer="https://login.microsoftonline.com/selnikel-tenant/v2.0",
        tenant_id="selnikel-tenant",
        db=mock_db,
    )

    assert user.id == "internal-usr-uuid-001"
    assert user.role_codes == ["engineer"]
    assert "document.read" in user.permissions
    assert "dept-engineering" in user.department_ids


@pytest.mark.asyncio
async def test_oidc_mode_cannot_bypass_external_identity_with_internal_uuid():
    """
    CRITICAL SECURITY TEST:
    In OIDC mode, an attacker token whose 'sub' matches an internal UserModel.id
    MUST NOT resolve to that internal user if there is no corresponding row in user_external_identities table.
    """
    settings.AUTH_MODE = "oidc"
    mock_db = AsyncMock()

    # External identity lookup returns None (unmapped)
    res_ext = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))
    mock_db.execute = AsyncMock(return_value=res_ext)

    user = await resolve_user_from_db_or_seed(
        sub="internal-admin-uuid-999",  # Attacker tries using internal admin UUID
        email="attacker@external.com",
        display_name="Attacker",
        issuer="https://foreign-idp.example.com",
        tenant_id="foreign-tenant",
        db=mock_db,
    )

    # Must strictly be Zero-Privilege user
    assert user.role_codes == []
    assert user.permissions == []
    assert user.department_ids == []
    assert user.has_permission("document.read") is False
    assert user.has_permission("admin.users.write") is False


@pytest.mark.asyncio
async def test_passive_or_disabled_user_revoked_all_privileges():
    """
    Verify that an inactive/disabled/suspended user account has all permissions and department access revoked.
    """
    mock_db = AsyncMock()

    # Mock UserExternalIdentity
    mock_ext_ident = MagicMock(spec=UserExternalIdentityModel)
    mock_ext_ident.user_id = "internal-usr-disabled-001"

    # Mock UserModel with status="disabled"
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = "internal-usr-disabled-001"
    mock_user.email = "disabled_user@selnikel.com.tr"
    mock_user.display_name = "Disabled User"
    mock_user.status = "disabled"

    res1 = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_ext_ident))))
    res2 = MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_user))))

    mock_db.execute = AsyncMock(side_effect=[res1, res2])

    settings.AUTH_MODE = "oidc"
    user = await resolve_user_from_db_or_seed(
        sub="ext-sub-disabled",
        email="disabled_user@selnikel.com.tr",
        display_name="Disabled User",
        issuer="https://auth.selnikel.com.tr",
        tenant_id="selnikel-tenant",
        db=mock_db,
    )

    assert user.status == "disabled"
    assert user.role_codes == []
    assert user.permissions == []
    assert user.department_ids == []
    assert user.has_permission("document.read") is False
    assert user.can_access_department("dept-engineering") is False


@pytest.mark.asyncio
async def test_auth_mode_bff_session_cookie():
    settings.AUTH_MODE = "bff"
    settings.SESSION_SECRET_KEY = "test-session-secret"

    import base64
    payload_dict = {
        "sub": "a0000000-0000-0000-0000-000000000002",
        "email": "engineer@selnikel.com.tr",
        "exp": int(time.time()) + 3600
    }
    payload_json = json.dumps(payload_dict)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        settings.SESSION_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    valid_cookie = f"{payload_b64}.{signature}"

    # Mock DB user
    mock_db = AsyncMock()
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = "a0000000-0000-0000-0000-000000000002"
    mock_user.email = "engineer@selnikel.com.tr"
    mock_user.display_name = "Engineer"
    mock_user.status = "active"

    async def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "role_permissions" in stmt_str:
            return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["document.read"]))))
        elif "user_roles" in stmt_str:
            return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["engineer"]))))
        elif "department_memberships" in stmt_str:
            return MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["dept-engineering"]))))
        elif "from users" in stmt_str:
            return MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_user), all=MagicMock(return_value=[mock_user]))))
        elif "count" in stmt_str:
            return MagicMock(scalar=MagicMock(return_value=0))
        else:
            return MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[]))))

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    
    async def mock_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = mock_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies={"selnikel_session": valid_cookie}) as ac:
        # 1. Valid signed session cookie
        res_cookie = await ac.get("/api/v1/documents")
        assert res_cookie.status_code == 200

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", cookies={"selnikel_session": f"{payload_b64}.bad_signature"}) as ac:
        # 2. Tampered cookie -> 401
        res_bad = await ac.get("/api/v1/documents")
        assert res_bad.status_code == 401


def test_startup_validation_fail_fast():
    # 1. Reject development auth in production
    settings.ENVIRONMENT = "production"
    settings.AUTH_MODE = "development"
    with pytest.raises(RuntimeError) as exc1:
        settings.validate_auth_configuration()
    assert "forbidden in production" in str(exc1.value).lower()

    # 2. Reject missing OIDC configuration in production
    settings.AUTH_MODE = "oidc"
    settings.OIDC_ISSUER = None
    settings.OIDC_CLIENT_ID = None
    with pytest.raises(RuntimeError) as exc2:
        settings.validate_auth_configuration()
    assert "requires OIDC_ISSUER and OIDC_CLIENT_ID" in str(exc2.value)
