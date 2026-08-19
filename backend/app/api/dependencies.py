"""
API Dependencies for Authentication, RBAC Authorization, and Departmental ABAC Isolation.
Supports strict separation of credential schemes by AUTH_MODE:
1. development: Explicit 'dev-token-<email>' or 'X-Dev-User' header only.
2. oidc: Cryptographically signed JWT tokens with signature, expiration, issuer, and audience validation.
3. bff: Cryptographically signed and verified session cookies.
"""
import hmac
import hashlib
import time
import json
from typing import Optional, Callable, Dict, Any
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from app.domain.identity.models import User
from app.db.session import get_db

security = HTTPBearer(auto_error=False)

# Seed Accounts for Development, Staging, and Test Scaffolding
SEED_USERS: Dict[str, User] = {
    "admin@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000001",
        email="admin@selnikel.com.tr",
        display_name="Sistem Yöneticisi",
        status="active",
        department_ids=["dept-engineering", "dept-manufacturing", "dept-service", "dept-quality"],
        role_codes=["admin"],
        permissions=[
            "document.read", "document.upload", "document.approve", "document.delete",
            "answer.create", "answer.approve", "export.create", "audit.read"
        ]
    ),
    "engineer@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000002",
        email="engineer@selnikel.com.tr",
        display_name="Ar-Ge Mühendisi",
        status="active",
        department_ids=["dept-engineering"],
        role_codes=["engineer"],
        permissions=["document.read", "document.upload", "answer.create", "export.create"]
    ),
    "service@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000003",
        email="service@selnikel.com.tr",
        display_name="Saha Servis Teknisyeni",
        status="active",
        department_ids=["dept-service"],
        role_codes=["service"],
        permissions=["document.read", "answer.create"]
    ),
    "approver@selnikel.com.tr": User(
        id="a0000000-0000-0000-0000-000000000004",
        email="approver@selnikel.com.tr",
        display_name="Başmühendis (Onay Yetkilisi)",
        status="active",
        department_ids=["dept-engineering", "dept-quality"],
        role_codes=["approver"],
        permissions=["document.read", "document.approve", "answer.create", "answer.approve", "export.create"]
    )
}


def _verify_session_cookie(cookie_value: str) -> Optional[User]:
    """Verifies HMAC signed session cookie payload."""
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
            import base64
            raw_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8") + b"==").decode("utf-8")
        except Exception:
            raw_json = payload_b64

        payload = json.loads(raw_json)
        if payload.get("exp", 0) < time.time():
            return None

        email = payload.get("email")
        return SEED_USERS.get(email)
    except Exception:
        return None


def _verify_oidc_jwt(token: str) -> User:
    """Verifies OIDC JWT cryptographic signature, expiry, issuer, and claims."""
    try:
        decode_kwargs: Dict[str, Any] = {
            "key": settings.JWT_SECRET_KEY,
            "algorithms": [settings.JWT_ALGORITHM],
        }
        if settings.OIDC_ISSUER:
            decode_kwargs["issuer"] = settings.OIDC_ISSUER
        if settings.OIDC_AUDIENCE:
            decode_kwargs["audience"] = settings.OIDC_AUDIENCE

        payload = jwt.decode(token, **decode_kwargs)
        email = payload.get("email") or payload.get("sub")
        if email and email in SEED_USERS:
            return SEED_USERS[email]

        # Dynamically build user from verified JWT claims
        return User(
            id=payload.get("sub", f"usr-{int(time.time())}"),
            email=email or "user@selnikel.com.tr",
            display_name=payload.get("name", "OIDC Authenticated User"),
            department_ids=payload.get("departments", ["dept-engineering"]),
            role_codes=payload.get("roles", ["engineer"]),
            permissions=payload.get("permissions", ["document.read", "answer.create"]),
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OIDC JWT doğrulama hatası: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_dev_user: Optional[str] = Header(default=None, alias="X-Dev-User"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email")
) -> User:
    """
    Extracts and strictly validates user identity according to settings.AUTH_MODE.
    Fails closed with 401 UNAUTHORIZED for missing/invalid credentials.
    """
    mode = settings.AUTH_MODE

    # Mode 1: DEVELOPMENT MODE
    if mode == "development":
        # 1a. Explicit dev header
        dev_email = x_dev_user or x_user_email
        if dev_email and dev_email in SEED_USERS:
            user = SEED_USERS[dev_email]
            request.state.user = user
            return user

        # 1b. Explicit dev bearer token 'dev-token-<email>'
        if auth_header:
            token = auth_header.credentials
            if token.startswith("dev-token-"):
                email = token.replace("dev-token-", "")
                if email in SEED_USERS:
                    user = SEED_USERS[email]
                    request.state.user = user
                    return user

        # 1c. Also allow valid OIDC JWT in dev mode if presented
        if auth_header and len(auth_header.credentials.split(".")) == 3:
            try:
                user = _verify_oidc_jwt(auth_header.credentials)
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
        user = _verify_oidc_jwt(auth_header.credentials)
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
        user = _verify_session_cookie(cookie_val)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş BFF oturum çerezi.",
                headers={"WWW-Authenticate": "Cookie"},
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Erişim reddedildi: Bu işlem için '{permission_code}' yetkisi gereklidir."
            )
        return user

    return permission_checker


def require_department(department_id: str) -> Callable:
    """FastAPI dependency factory enforcing ABAC department isolation."""
    async def department_checker(
        user: User = Depends(get_current_user)
    ) -> User:
        if not user.can_access_department(department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Erişim reddedildi: '{department_id}' departmanına erişim yetkiniz bulunmuyor."
            )
        return user

    return department_checker
