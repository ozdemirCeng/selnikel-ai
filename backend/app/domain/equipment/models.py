"""
Domain Models for Industrial Equipment & Models (Boilers, Burners, Fans, Pressure Vessels).
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class EquipmentType(str, Enum):
    BOILER = "boiler"
    BURNER = "burner"
    FAN = "fan"
    PRESSURE_VESSEL = "pressure_vessel"
    OTHER = "other"

class Equipment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    equipment_type: EquipmentType
    model_code: str  # e.g., "SB-100", "GLS-35", "FAN-RAD-600"
    serial_number: Optional[str] = None
    name: str
    department_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"  # "active" | "retired"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
