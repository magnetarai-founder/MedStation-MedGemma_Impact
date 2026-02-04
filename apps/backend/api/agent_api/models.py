"""
Pydantic models for Agent API

Request/Response models for all agent endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class AgentTaskRequest(BaseModel):
    """Request to execute a task with agent"""

    task: str = Field(..., description="Task description")
    workspace_path: str = Field(..., description="Workspace root path")
    auto_approve: bool = Field(
        False, description="Auto-approve destructive operations (dangerous!)"
    )
    recent_files: list[str] | None = Field(None, description="Recently active files")
    current_errors: str | None = Field(None, description="Current errors/terminal output")


class AgentStatusResponse(BaseModel):
    """Agent execution status"""

    task_id: str
    status: str
    current_plan: dict[str, Any] | None = None
    execution_log: list[dict[str, Any]] | None = None


class MultiAgentRequest(BaseModel):
    """Request for multi-agent execution"""

    task: str = Field(..., description="Task description")
    workspace_path: str = Field(..., description="Workspace root path")
    strategy: str = Field(
        "sequential",
        description="Coordination strategy: sequential, parallel, pipeline, collaborative",
    )
    auto_approve: bool = Field(False, description="Auto-approve operations")


class FeedbackRequest(BaseModel):
    """User feedback on task execution"""

    task_id: str
    agent_role: str
    feedback_type: str  # positive, negative, neutral
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5 stars")
    comment: str | None = None


class CustomToolRequest(BaseModel):
    """Request to register custom tool"""

    name: str
    description: str
    tool_type: str  # python_function, shell_script, api_call
    parameters: list[dict[str, Any]]
    implementation: str
    category: str = "custom"
    tags: list[str] = []
