from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class AgentStep(BaseModel):
    step_number: int
    thought: str
    tool_call: Optional[ToolCallRequest] = None
    tool_result: Optional[ToolCallResult] = None


class AgentExecutionResponse(BaseModel):
    query: str
    final_answer: str
    steps: List[AgentStep] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0
