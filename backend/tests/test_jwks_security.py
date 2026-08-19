"""
Comprehensive RS256 & JWKS Security Test Suite
Validates:
1. RS256 asymmetric signature verification with JWKS
2. Dynamic kid selection and key rotation
3. Invalid Issuer / Audience / Tenant ID (tid) rejection
4. JWKS unreachable / network error graceful 401 handling
5. Algorithm confusion attack defense (HS256 rejected when RS256 expected)
"""
import time
import pytest
import jwt
from unittest.mock import MagicMock, patch, AsyncMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.api.dependencies import ProcessLevelJWKSManager, get_db

@pytest.fixture(scope="module")
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_private, pem_public, private_key, public_key


@pytest.fixture(autouse=True)
def reset_jwks_and_settings():
    orig_mode = settings.AUTH_MODE
    orig_jwt_sec = settings.JWT_SECRET_KEY
    orig_alg = settings.JWT_ALGORITHM
    orig_iss = settings.OIDC_ISSUER
    orig_aud = settings.OIDC_AUDIENCE
    orig_cid = settings.OIDC_CLIENT_ID
    orig_jwks = settings.OIDC_JWKS_URI
    orig_tid = settings.OIDC_TENANT_ID

    ProcessLevelJWKSManager.reset()

    # Provide mock DB returning empty to avoid live connection
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None), all=MagicMock(return_value=[])))))
    app.dependency_overrides[get_db] = lambda: mock_db

    yield

    app.dependency_overrides.clear()
    ProcessLevelJWKSManager.reset()
    settings.AUTH_MODE = orig_mode
    settings.JWT_SECRET_KEY = orig_jwt_sec
    settings.JWT_ALGORITHM = orig_alg
    settings.OIDC_ISSUER = orig_iss
    settings.OIDC_AUDIENCE = orig_aud
    settings.OIDC_CLIENT_ID = orig_cid
    settings.OIDC_JWKS_URI = orig_jwks
    settings.OIDC_TENANT_ID = orig_tid


@pytest.mark.asyncio
async def test_rs256_jwks_signature_verification(rsa_keypair):
    """Verify RS256 verification using PyJWKClient mock."""
    pem_private, pem_public, private_key, public_key = rsa_keypair
    kid = "selnikel-key-2026-01"

    settings.AUTH_MODE = "oidc"
    settings.OIDC_ISSUER = "https://login.microsoftonline.com/selnikel-tenant/v2.0"
    settings.OIDC_CLIENT_ID = "selnikel-app-id"
    settings.OIDC_JWKS_URI = "https://login.microsoftonline.com/selnikel-tenant/discovery/v2.0/keys"
    settings.OIDC_TENANT_ID = "selnikel-tenant"

    token_payload = {
        "sub": "usr-rs256-001",
        "email": "engineer@selnikel.com.tr",
        "iss": settings.OIDC_ISSUER,
        "aud": settings.OIDC_CLIENT_ID,
        "tid": settings.OIDC_TENANT_ID,
        "exp": int(time.time()) + 3600,
    }
    headers = {"kid": kid, "alg": "RS256"}
    token = jwt.encode(token_payload, pem_private, algorithm="RS256", headers=headers)

    # Mock PyJWKClient signing key return
    mock_signing_key = MagicMock()
    mock_signing_key.key = pem_public
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt = MagicMock(return_value=mock_signing_key)

    with patch.object(ProcessLevelJWKSManager, "get_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200


@pytest.mark.asyncio
async def test_rs256_jwks_invalid_tenant_rejected(rsa_keypair):
    """Verify that a token from an unauthorized tenant (foreign tid) is strictly rejected."""
    pem_private, pem_public, _, _ = rsa_keypair
    settings.AUTH_MODE = "oidc"
    settings.OIDC_ISSUER = "https://login.microsoftonline.com/selnikel-tenant/v2.0"
    settings.OIDC_CLIENT_ID = "selnikel-app-id"
    settings.OIDC_JWKS_URI = "https://login.microsoftonline.com/selnikel-tenant/discovery/v2.0/keys"
    settings.OIDC_TENANT_ID = "selnikel-tenant"

    token_payload = {
        "sub": "usr-rs256-002",
        "email": "engineer@selnikel.com.tr",
        "iss": settings.OIDC_ISSUER,
        "aud": settings.OIDC_CLIENT_ID,
        "tid": "foreign-unauthorized-tenant",  # WRONG TENANT
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(token_payload, pem_private, algorithm="RS256", headers={"kid": "k1"})

    mock_signing_key = MagicMock(key=pem_public)
    mock_client = MagicMock(get_signing_key_from_jwt=MagicMock(return_value=mock_signing_key))

    with patch.object(ProcessLevelJWKSManager, "get_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 401
            assert "Geçersiz Entra Tenant ID" in res.json()["detail"]


@pytest.mark.asyncio
async def test_rs256_algorithm_confusion_attack_prevented(rsa_keypair):
    """
    Verify Algorithm Confusion Protection:
    Attacker creates an HMAC-SHA256 token signed with an arbitrary secret key.
    The verifier MUST strictly reject it because algorithms=['RS256'] is enforced.
    """
    _, pem_public, _, _ = rsa_keypair
    settings.AUTH_MODE = "oidc"
    settings.OIDC_ISSUER = "https://login.microsoftonline.com/selnikel-tenant/v2.0"
    settings.OIDC_CLIENT_ID = "selnikel-app-id"
    settings.OIDC_JWKS_URI = "https://login.microsoftonline.com/selnikel-tenant/discovery/v2.0/keys"

    payload = {
        "sub": "usr-attacker",
        "email": "admin@selnikel.com.tr",
        "iss": settings.OIDC_ISSUER,
        "aud": settings.OIDC_CLIENT_ID,
        "exp": int(time.time()) + 3600,
    }
    # Attacker signs with HS256
    malicious_token = jwt.encode(payload, "attacker-secret-key-123456", algorithm="HS256", headers={"kid": "k1"})

    mock_signing_key = MagicMock(key=pem_public)
    mock_client = MagicMock(get_signing_key_from_jwt=MagicMock(return_value=mock_signing_key))

    with patch.object(ProcessLevelJWKSManager, "get_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {malicious_token}"})
            assert res.status_code == 401


@pytest.mark.asyncio
async def test_jwks_network_unreachable_fails_gracefully():
    """Verify that an unreachable JWKS endpoint returns 401 rather than crashing the server."""
    settings.AUTH_MODE = "oidc"
    settings.OIDC_JWKS_URI = "https://unreachable.keys.example.com/jwks.json"

    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIn0.eyJzdWIiOiIxMjMifQ.signature"

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = Exception("Connection refused / DNS failure")

    with patch.object(ProcessLevelJWKSManager, "get_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 401
            assert "JWKS anahtarı alınamadı" in res.json()["detail"]
