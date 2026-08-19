"""
Domain Models for Organizational Hierarchy and Departments
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

class Department(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    code: str  # 'engineering' | 'manufacturing' | 'service' | 'quality' | 'management'
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
