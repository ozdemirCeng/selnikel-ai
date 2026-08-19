"""
SQLAlchemy 2.0 ORM Models for Equipment and Document-Equipment Associations.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from app.db.base import Base

def gen_uuid():
    return str(uuid.uuid4())

class EquipmentModel(Base):
    __tablename__ = "equipment"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    equipment_type = Column(String(50), nullable=False, index=True)
    model_code = Column(String(100), unique=True, nullable=False, index=True)
    serial_number = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    department_id = Column(String(36), nullable=True)
    attributes = Column(JSON, nullable=False, default={})
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class DocumentEquipmentModel(Base):
    __tablename__ = "document_equipment"

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    equipment_id = Column(String(36), ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True)
