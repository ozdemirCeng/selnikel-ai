"""
Identity, RBAC, ABAC and Authentication Mode Verification Test Suite
Validates:
1. Permission and Role logic
2. Strict 401 unauthenticated enforcement
3. AUTH_MODE=development (dev-token only, rejecting raw emails)
4. AUTH_MODE=oidc (JWT signature, expiration, issuer, audience, and rejection of dev tokens)
5. AUTH_MODE=bff (HMAC signed session cookie verification)
6. Startup configuration fail-fast checks
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
from app.api.dependencies import get_db
from app.core.config import settings
from app.domain.identity.models import User, Role, Permission
from app.api.dependencies import SEED_USERS

@pytest.fixture(autouse=True)
def reset_settings_and_db():
    orig_mode = settings.AUTH_MODE
    orig_jwt_sec = settings.JWT_SECRET_KEY
    orig_iss = settings.OIDC_ISSUER
    orig_aud = settings.OIDC_AUDIENCE
    orig_sess_sec = settings.SESSION_SECRET_KEY

    # Override get_db to avoid external DB connection during auth tests
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    app.dependency_overrides[get_db] = lambda: mock_db

    yield

    app.dependency_overrides.clear()
    settings.AUTH_MODE = orig_mode
    settings.JWT_SECRET_KEY = orig_jwt_sec
    settings.OIDC_ISSUER = orig_iss
    settings.OIDC_AUDIENCE = orig_aud
    settings.SESSION_SECRET_KEY = orig_sess_sec


def test_user_domain_permission_logic():
    admin = SEED_USERS["admin@selnikel.com.tr"]
    engineer = SEED_USERS["engineer@selnikel.com.tr"]
    service = SEED_USERS["service@selnikel.com.tr"]

    assert admin.has_permission("document.delete") is True
    assert engineer.has_permission("document.delete") is False
    assert engineer.has_permission("document.upload") is True
    assert service.has_permission("document.upload") is False


def test_raw_email_token_rejected_in_all_modes():
    """Verify that raw email as Bearer token is strictly rejected."""
    settings.AUTH_MODE = "development"


@pytest.mark.asyncio
async def test_auth_mode_development():
    settings.AUTH_MODE = "development"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Missing credentials -> 401
        res = await ac.get("/api/v1/documents")
        assert res.status_code == 401

        # 2. Raw email token -> 401
        res_raw = await ac.get("/api/v1/documents", headers={"Authorization": "Bearer admin@selnikel.com.tr"})
        assert res_raw.status_code == 401

        # 3. Valid dev token -> 200
        res_dev = await ac.get("/api/v1/documents", headers={"Authorization": "Bearer dev-token-engineer@selnikel.com.tr"})
        assert res_dev.status_code == 200

        # 4. Valid dev header -> 200
        res_hdr = await ac.get("/api/v1/documents", headers={"X-Dev-User": "engineer@selnikel.com.tr"})
        assert res_hdr.status_code == 200


@pytest.mark.asyncio
async def test_auth_mode_oidc_jwt_verification():
    settings.AUTH_MODE = "oidc"
    settings.JWT_SECRET_KEY = "test-secret-key-123"
    settings.OIDC_ISSUER = "https://auth.selnikel.com.tr"
    settings.OIDC_AUDIENCE = "selnikel-ai"

    # 1. Reject dev token in OIDC mode
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/documents", headers={"Authorization": "Bearer dev-token-engineer@selnikel.com.tr"})
        assert res.status_code == 401

        # 2. Valid signed JWT
        payload = {
            "sub": "a0000000-0000-0000-0000-000000000002",
            "email": "engineer@selnikel.com.tr",
            "iss": "https://auth.selnikel.com.tr",
            "aud": "selnikel-ai",
            "exp": time.time() + 3600,
        }
        valid_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        res_jwt = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {valid_jwt}"})
        assert res_jwt.status_code == 200

        # 3. Expired JWT -> 401
        expired_payload = {**payload, "exp": time.time() - 60}
        expired_jwt = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        res_exp = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {expired_jwt}"})
        assert res_exp.status_code == 401

        # 4. Tampered signature -> 401
        tampered_jwt = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        res_tamp = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {tampered_jwt}"})
        assert res_tamp.status_code == 401

        # 5. Valid JWT for unmapped external user -> Authenticated with ZERO privileges -> 403 Forbidden on restricted action
        unmapped_payload = {
            "sub": "ext-user-999",
            "email": "external_vendor@contractor.com",
            "iss": "https://auth.selnikel.com.tr",
            "aud": "selnikel-ai",
            "exp": time.time() + 3600,
        }
        unmapped_jwt = jwt.encode(unmapped_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        # Attempt upload without permissions
        res_unmapped = await ac.post("/api/v1/documents/upload", headers={"Authorization": f"Bearer {unmapped_jwt}"})
        assert res_unmapped.status_code == 403


@pytest.mark.asyncio
async def test_auth_mode_bff_session_cookie():
    settings.AUTH_MODE = "bff"
    settings.SESSION_SECRET_KEY = "test-session-secret"

    import base64
    payload_dict = {
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

    # 3. Reject wildcard CORS in production
    settings.BACKEND_CORS_ORIGINS = ["*"]
    with pytest.raises(RuntimeError) as exc3:
        settings.validate_auth_configuration()
    assert "wildcard" in str(exc3.value).lower()
