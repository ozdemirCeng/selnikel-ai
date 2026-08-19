from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    query: str = Field(..., description="Engineering question, calculation prompt, or technical report task.")
    max_steps: int = Field(default=5, ge=1, le=10, description="Maximum ReAct reasoning steps.")


class ToolParameterSchema(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinitionSchema(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameterSchema] = Field(default_factory=list)


class ToolCallRequestSchema(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResultSchema(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class AgentStepSchema(BaseModel):
    step_number: int
    thought: str
    tool_call: Optional[ToolCallRequestSchema] = None
    tool_result: Optional[ToolCallResultSchema] = None


class AgentRunResponse(BaseModel):
    query: str
    final_answer: str
    steps: List[AgentStepSchema] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0


class PDFReportRequest(BaseModel):
    markdown_content: str = Field(..., description="Markdown content of the report to render into PDF.")
    title: Optional[str] = Field(default="Selnikel Teknik Raporu", description="PDF report document title.")

