"""
Domain Models for Identity & Role-Based Access Control (RBAC)
Pure Python dataclasses / Pydantic models with zero framework dependencies.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class Permission(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    code: str
    name: str
    description: Optional[str] = None

class Role(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    code: str  # 'admin' | 'engineer' | 'service' | 'viewer' | 'approver'
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    display_name: str
    status: str = "active"  # "active" | "disabled"
    department_ids: List[str] = Field(default_factory=list)
    role_codes: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def has_permission(self, permission_code: str) -> bool:
        if "admin" in self.role_codes or "super_admin" in self.role_codes or "*" in self.permissions:
            return True
        return permission_code in self.permissions

    def can_access_department(self, department_id: str) -> bool:
        if "admin" in self.role_codes or "super_admin" in self.role_codes or "*" in self.permissions or "dept-management" in self.department_ids:
            return True
        clean_target = department_id.replace("dept-", "").lower()
        clean_user_depts = [d.replace("dept-", "").lower() for d in self.department_ids]
        return department_id in self.department_ids or clean_target in clean_user_depts

    def has_department_access(self, department_id: str) -> bool:
        return self.can_access_department(department_id)
