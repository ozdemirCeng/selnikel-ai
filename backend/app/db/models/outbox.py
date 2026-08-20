"""
SQLAlchemy 2.0 ORM Model for Transactional Outbox Events.
Guarantees at-least-once dual-write delivery to Qdrant vector index and event consumers.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    Text,
)
from app.db.base import Base


def gen_uuid():
    return str(uuid.uuid4())


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    event_id = Column(String(36), primary_key=True, default=gen_uuid)
    aggregate_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending | processing | completed | failed
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=5, nullable=False)
    last_error = Column(Text, nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)