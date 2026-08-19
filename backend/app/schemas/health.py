from typing import Dict, Literal
from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    status: Literal["healthy", "unhealthy", "disabled"]
    latency_ms: float = Field(..., description="Latency of health check in milliseconds")
    details: str = Field(default="", description="Additional status details or error message")


class HealthCheckResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    project: str
    environment: str
    version: str
    components: Dict[str, ServiceComponentStatus]
