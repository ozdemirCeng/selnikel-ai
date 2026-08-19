"""
Identity, RBAC, and Department ABAC Test Suite
Validates User domain model permissions, FastAPI dependency enforcement, and forbidden access handling.
"""
import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from app.domain.identity.models import User, Role, Permission
from app.api.dependencies import (
    get_current_user,
    require_permission,
    require_department,
    SEED_USERS,
)

# Test FastAPI app with protected routes
test_app = FastAPI()

@test_app.get("/api/test/public")
async def public_route():
    return {"status": "public"}

@test_app.get("/api/test/profile")
async def profile_route(user: User = Depends(get_current_user)):
    return {"email": user.email, "display_name": user.display_name, "roles": user.role_codes}

@test_app.get("/api/test/upload-doc")
async def upload_doc_route(user: User = Depends(require_permission("document.upload"))):
    return {"status": "allowed", "user": user.email}

@test_app.get("/api/test/approve-doc")
async def approve_doc_route(user: User = Depends(require_permission("document.approve"))):
    return {"status": "approved", "user": user.email}

@test_app.get("/api/test/engineering-data")
async def engineering_dept_route(user: User = Depends(require_department("dept-engineering"))):
    return {"status": "ok", "department": "dept-engineering"}

@test_app.get("/api/test/manufacturing-data")
async def manufacturing_dept_route(user: User = Depends(require_department("dept-manufacturing"))):
    return {"status": "ok", "department": "dept-manufacturing"}

client = TestClient(test_app)


def test_user_domain_permission_logic():
    """Verify that User entity evaluates permissions correctly based on roles."""
    admin = SEED_USERS["admin@selnikel.com.tr"]
    engineer = SEED_USERS["engineer@selnikel.com.tr"]
    service = SEED_USERS["service@selnikel.com.tr"]

    # Admin has all permissions implicitly
    assert admin.has_permission("document.approve") is True
    assert admin.has_permission("audit.read") is True
    assert admin.can_access_department("dept-any") is True

    # Engineer has document.upload, but not document.approve
    assert engineer.has_permission("document.upload") is True
    assert engineer.has_permission("document.approve") is False
    assert engineer.can_access_department("dept-engineering") is True
    assert engineer.can_access_department("dept-manufacturing") is False

    # Service has answer.create, but not document.upload
    assert service.has_permission("answer.create") is True
    assert service.has_permission("document.upload") is False


def test_auth_headers_and_roles():
    """Verify endpoint authentication with X-User-Email and Bearer tokens."""
    # 1. As Engineer
    res = client.get("/api/test/profile", headers={"X-User-Email": "engineer@selnikel.com.tr"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "engineer@selnikel.com.tr"
    assert "engineer" in data["roles"]

    # 2. As Admin via Bearer token
    res = client.get("/api/test/profile", headers={"Authorization": "Bearer token-admin@selnikel.com.tr"})
    assert res.status_code == 200
    assert "admin" in res.json()["roles"]


def test_rbac_permission_enforcement():
    """Verify that 403 Forbidden is returned when user lacks required permission."""
    # 1. Engineer CAN upload
    res = client.get("/api/test/upload-doc", headers={"X-User-Email": "engineer@selnikel.com.tr"})
    assert res.status_code == 200
    assert res.json()["status"] == "allowed"

    # 2. Service CANNOT upload (403 Forbidden)
    res = client.get("/api/test/upload-doc", headers={"X-User-Email": "service@selnikel.com.tr"})
    assert res.status_code == 403
    assert "Erişim reddedildi" in res.json()["detail"]

    # 3. Engineer CANNOT approve (403 Forbidden)
    res = client.get("/api/test/approve-doc", headers={"X-User-Email": "engineer@selnikel.com.tr"})
    assert res.status_code == 403

    # 4. Approver CAN approve
    res = client.get("/api/test/approve-doc", headers={"X-User-Email": "approver@selnikel.com.tr"})
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_department_abac_enforcement():
    """Verify that users are restricted to their authorized departments."""
    # 1. Engineer has access to Engineering
    res = client.get("/api/test/engineering-data", headers={"X-User-Email": "engineer@selnikel.com.tr"})
    assert res.status_code == 200

    # 2. Engineer CANNOT access Manufacturing (403 Forbidden)
    res = client.get("/api/test/manufacturing-data", headers={"X-User-Email": "engineer@selnikel.com.tr"})
    assert res.status_code == 403
    assert "departmanına erişim yetkiniz bulunmuyor" in res.json()["detail"]

    # 3. Admin can access Manufacturing
    res = client.get("/api/test/manufacturing-data", headers={"X-User-Email": "admin@selnikel.com.tr"})
    assert res.status_code == 200
