"""
Terminal API Models

Pydantic models for terminal request/response data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SpawnTerminalResponseData(BaseModel):
    """Response data for terminal spawn"""
    terminal_id: str = Field(..., alias="terminalId")
    terminal_app: str = Field(..., alias="terminalApp")
    workspace_root: str = Field(..., alias="workspaceRoot")
    active_count: int = Field(..., alias="activeCount")
    message: str

    class Config:
        populate_by_name = True


class BashAssistRequest(BaseModel):
    """Request for bash assist"""
    input: str
    session_id: Optional[str] = None
    cwd: Optional[str] = None


class BashAssistResponse(BaseModel):
    """Response from bash assist"""
    input_type: str  # 'nl', 'bash', 'ambiguous'
    confidence: float
    suggested_command: Optional[str]
    is_safe: bool
    safety_warning: Optional[str]
    improvements: List[str]
