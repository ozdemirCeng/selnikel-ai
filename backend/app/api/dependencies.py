"""
Authentication, Identity, RBAC & ABAC Dependencies for Selnikel AI.
Implements:
1. Multi-mode authentication segregation: 'development', 'oidc', 'bff'.
2. Process-level cached JWKS verification for Microsoft Entra ID / OIDC (RS256/ES256).
3. Strict algorithm confusion protection (whitelisted algorithms only).
4. Tenant ID (tid) and Audience (aud) validation.
5. Database-backed authorization: maps verified token sub/email -> DB UserModel -> Roles -> Permissions.
6. Zero-privilege fallback (0 roles, 0 departments, 0 permissions) for unassigned / unmapped accounts.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.db.models.identity import (
    UserModel,
    RoleModel,
    PermissionModel,
    UserRoleModel,
    RolePermissionModel,
    DepartmentMembershipModel,
    DepartmentModel,
    UserExternalIdentityModel,
)
from app.domain.identity.models import User

security = HTTPBearer(auto_error=False)

# Development Seed Users (used exclusively when AUTH_MODE=development)
SEED_USERS: Dict[str, User] = {
    "admin@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000001",
        email="admin@selnikel.com.tr",
        display_name="Sistem Yöneticisi",
        department_ids=["dept-engineering", "dept-service", "dept-production", "dept-r_and_d", "dept-management"],
        role_codes=["super_admin"],
        permissions=[
            "document.read", "document.upload", "document.delete", "document.approve",
            "answer.create", "answer.approve", "export.create", "audit.view", "system.manage"
        ]
    ),
    "engineer@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000002",
        email="engineer@selnikel.com.tr",
        display_name="Kazan Tasarım Mühendisi",
        department_ids=["dept-engineering", "dept-r_and_d"],
        role_codes=["engineer"],
        permissions=["document.read", "document.upload", "answer.create", "export.create"]
    ),
    "service@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000003",
        email="service@selnikel.com.tr",
        display_name="Saha Servis Teknisyeni",
        department_ids=["dept-service"],
        role_codes=["service_tech"],
        permissions=["document.read", "answer.create"]
    ),
    "approver@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000004",
        email="approver@selnikel.com.tr",
        display_name="Başmühendis Onaylayıcı",
        department_ids=["dept-engineering", "dept-service", "dept-production", "dept-r_and_d"],
        role_codes=["approver"],
        permissions=["document.read", "document.approve", "answer.create", "answer.approve", "export.create"]
    )
}


class ProcessLevelJWKSManager:
    """
    Process-level singleton managing PyJWKClient instance and key caching across requests.
    Prevents recreating HTTP clients on every incoming token verification.
    """
    _clients: Dict[str, jwt.PyJWKClient] = {}

    @classmethod
    def get_client(cls, jwks_uri: str) -> jwt.PyJWKClient:
        if jwks_uri not in cls._clients:
            cls._clients[jwks_uri] = jwt.PyJWKClient(
                jwks_uri,
                cache_keys=True,
                max_cached_keys=32,
                cache_jwk_set=True,
                lifespan=3600
            )
        return cls._clients[jwks_uri]

    @classmethod
    def reset(cls):
        cls._clients.clear()


def _verify_session_cookie(cookie_value: str) -> Optional[Dict[str, Any]]:
    """Verifies HMAC signed session cookie payload and returns payload dict."""
    try:
        parts = cookie_value.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(
            settings.SESSION_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Decode base64 or json string
        try:
            raw_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8") + b"==").decode("utf-8")
        except Exception:
            raw_json = payload_b64

        payload = json.loads(raw_json)
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def _verify_oidc_jwt_claims(token: str) -> Dict[str, Any]:
    """
    Verifies OIDC / Entra ID JWT cryptographic signature, expiry, issuer, audience, and tenant.
    Enforces strict algorithm whitelisting to prevent algorithm confusion attacks.
    """
    try:
        # Determine verification key: JWKS URI (asymmetric) or Secret Key (symmetric / test)
        key = settings.JWT_SECRET_KEY
        expected_algorithm = settings.JWT_ALGORITHM

        if settings.OIDC_JWKS_URI:
            try:
                jwks_client = ProcessLevelJWKSManager.get_client(settings.OIDC_JWKS_URI)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                key = signing_key.key
                expected_algorithm = "RS256"
            except Exception as jwks_err:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"JWKS anahtarı alınamadı: {str(jwks_err)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        decode_kwargs: Dict[str, Any] = {
            "key": key,
            "algorithms": [expected_algorithm],  # Strictly whitelisted algorithm
            "options": {
                "verify_exp": True,
                "verify_iss": bool(settings.OIDC_ISSUER),
                "verify_aud": bool(settings.OIDC_AUDIENCE or settings.OIDC_CLIENT_ID),
            },
        }
        if settings.OIDC_ISSUER:
            decode_kwargs["issuer"] = settings.OIDC_ISSUER

        target_audience = settings.OIDC_AUDIENCE or settings.OIDC_CLIENT_ID
        if target_audience:
            decode_kwargs["audience"] = target_audience

        payload = jwt.decode(token, **decode_kwargs)

        # Microsoft Entra ID Tenant Verification
        if settings.OIDC_TENANT_ID:
            token_tid = payload.get("tid")
            if token_tid != settings.OIDC_TENANT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Geçersiz Entra Tenant ID: {token_tid}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OIDC JWT doğrulama hatası: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def resolve_user_from_db_or_seed(
    sub: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    issuer: Optional[str] = None,
    tenant_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> User:
    """
    Resolves authorization permissions for an identity.
    In OIDC/BFF mode:
      1. Resolves external identity from user_external_identities table (issuer + subject + optional tenant_id).
      2. If mapped, loads internal UserModel -> Roles -> Permissions -> Departments.
      3. If DB is unavailable, fails closed by raising 503 Service Unavailable.
      4. If unmapped in DB, strictly returns Zero-Privilege User (0 roles, 0 permissions, 0 departments).
    In Development mode ONLY:
      Falls back to SEED_USERS dictionary for local testing without DB.
    """
    # 1. Database Lookup (Mandatory in OIDC / BFF modes)
    if db is not None:
        try:
            user_model = None

            # 1a. Check UserExternalIdentityModel mapping (issuer + subject + tenant)
            if issuer:
                ext_query = select(UserExternalIdentityModel).where(
                    and_(
                        UserExternalIdentityModel.subject == sub,
                        UserExternalIdentityModel.issuer == issuer,
                    )
                )
                if tenant_id:
                    ext_query = ext_query.where(UserExternalIdentityModel.tenant_id == tenant_id)
                ext_res = await db.execute(ext_query)
                ext_identity = ext_res.scalars().first()
                if ext_identity:
                    user_res = await db.execute(select(UserModel).where(UserModel.id == ext_identity.user_id))
                    user_model = user_res.scalars().first()

            # 1b. Fallback to direct internal user id
            if user_model is None:
                user_res = await db.execute(select(UserModel).where(UserModel.id == sub))
                user_model = user_res.scalars().first()

            if (
                user_model is not None
                and hasattr(user_model, "id")
                and isinstance(getattr(user_model, "email", None), str)
                and isinstance(getattr(user_model, "status", None), str)
            ):
                # Query user roles
                roles_query = (
                    select(RoleModel.code)
                    .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
                    .where(UserRoleModel.user_id == user_model.id)
                )
                roles_res = await db.execute(roles_query)
                role_codes = list(roles_res.scalars().all())

                # Query user permissions through roles
                perms_query = (
                    select(PermissionModel.code)
                    .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
                    .join(UserRoleModel, UserRoleModel.role_id == RolePermissionModel.role_id)
                    .where(UserRoleModel.user_id == user_model.id)
                )
                perms_res = await db.execute(perms_query)
                permissions = list(perms_res.scalars().all())

                # Query department memberships
                depts_query = (
                    select(DepartmentModel.code)
                    .join(DepartmentMembershipModel, DepartmentMembershipModel.department_id == DepartmentModel.id)
                    .where(DepartmentMembershipModel.user_id == user_model.id)
                )
                depts_res = await db.execute(depts_query)
                dept_codes = list(depts_res.scalars().all())

                return User(
                    id=str(user_model.id),
                    email=str(user_model.email),
                    display_name=str(user_model.display_name),
                    status=str(user_model.status),
                    department_ids=[str(d) for d in dept_codes],
                    role_codes=[str(r) for r in role_codes],
                    permissions=[str(p) for p in permissions],
                )
        except Exception as db_err:
            logger.error(f"Database user resolution error: {db_err}")
            if settings.AUTH_MODE != "development":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Kimlik ve yetkilendirme veri tabanına erişilemedi. Güvenlik gereği istek durduruldu (Fail-closed).",
                )

    # 2. SEED_USERS check ONLY IN DEVELOPMENT MODE
    if settings.AUTH_MODE == "development":
        if email and email in SEED_USERS:
            return SEED_USERS[email]
        if sub in SEED_USERS:
            return SEED_USERS[sub]

    # 3. Fail-Closed / Zero-Privilege Model in Production/OIDC/BFF:
    # Unmapped external users receive ZERO permissions, ZERO roles, and ZERO department access.
    logger.warning(f"Unmapped external identity '{sub}' (issuer: {issuer}) assigned ZERO privileges.")
    return User(
        id=sub,
        email=email or "unknown@selnikel.com.tr",
        display_name=display_name or "Unassigned User",
        status="unassigned",
        department_ids=[],
        role_codes=[],
        permissions=[],
    )


async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_dev_user: Optional[str] = Header(default=None, alias="X-Dev-User"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts and strictly validates user identity according to settings.AUTH_MODE.
    Fails closed with 401 UNAUTHORIZED for missing/invalid credentials.
    """
    mode = settings.AUTH_MODE

    # Mode 1: DEVELOPMENT MODE
    if mode == "development":
        dev_email = x_dev_user or x_user_email
        if dev_email and dev_email in SEED_USERS:
            user = SEED_USERS[dev_email]
            request.state.user = user
            return user

        if auth_header:
            token = auth_header.credentials
            if token.startswith("dev-token-"):
                email = token.replace("dev-token-", "")
                if email in SEED_USERS:
                    user = SEED_USERS[email]
                    request.state.user = user
                    return user

        if auth_header and len(auth_header.credentials.split(".")) == 3:
            try:
                payload = _verify_oidc_jwt_claims(auth_header.credentials)
                sub = str(payload.get("sub") or payload.get("oid") or f"usr-{int(time.time())}")
                email = payload.get("email") or payload.get("preferred_username") or payload.get("upn")
                name = payload.get("name", "OIDC User")
                issuer = payload.get("iss")
                tenant_id = payload.get("tid")
                user = await resolve_user_from_db_or_seed(
                    sub=sub,
                    email=email,
                    display_name=name,
                    issuer=issuer,
                    tenant_id=tenant_id,
                    db=db,
                )
                request.state.user = user
                return user
            except HTTPException:
                pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulaması gereklidir: 'X-Dev-User' başlığı veya 'dev-token-<email>' Bearer belirteci bulunamadı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Mode 2: OIDC JWT MODE
    elif mode == "oidc":
        if not auth_header or not auth_header.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OIDC Bearer JWT token gereklidir.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = _verify_oidc_jwt_claims(auth_header.credentials)
        sub = str(payload.get("sub") or payload.get("oid") or f"usr-{int(time.time())}")
        email = payload.get("email") or payload.get("preferred_username") or payload.get("upn")
        name = payload.get("name", "OIDC User")
        issuer = payload.get("iss")
        tenant_id = payload.get("tid")
        user = await resolve_user_from_db_or_seed(
            sub=sub,
            email=email,
            display_name=name,
            issuer=issuer,
            tenant_id=tenant_id,
            db=db,
        )
        request.state.user = user
        return user

    # Mode 3: BFF SESSION COOKIE MODE
    elif mode == "bff":
        cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not cookie_val:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"BFF oturum çerezi ('{settings.SESSION_COOKIE_NAME}') bulunamadı.",
                headers={"WWW-Authenticate": "Cookie"},
            )
        payload = _verify_session_cookie(cookie_val)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş BFF oturum çerezi.",
                headers={"WWW-Authenticate": "Cookie"},
            )
        sub = str(payload.get("sub") or f"usr-{int(time.time())}")
        email = payload.get("email")
        name = payload.get("name", "BFF User")
        user = await resolve_user_from_db_or_seed(
            sub=sub,
            email=email,
            display_name=name,
            db=db,
        )
        request.state.user = user
        return user

    # Fallback safety guard
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Desteklenmeyen kimlik doğrulama modu.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission_code: str) -> Callable:
    """FastAPI dependency factory enforcing RBAC permission checks."""
    async def permission_checker(
        request: Request,
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.has_permission(permission_code):
            logger.warning(
                f"Access Denied: User '{user.email}' (roles: {user.role_codes}) lacks permission '{permission_code}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Yetki yetersiz: Bu işlem için '{permission_code}' izni gereklidir.",
            )
        return user

    return permission_checker


def require_department(department_id: str) -> Callable:
    """FastAPI dependency factory enforcing ABAC department access checks."""
    async def department_checker(
        request: Request,
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.has_department_access(department_id):
            logger.warning(
                f"Access Denied: User '{user.email}' cannot access department '{department_id}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Departman erişim engeli: '{department_id}' verilerine erişim izniniz bulunmamaktadır.",
            )
        return user

    return department_checker
