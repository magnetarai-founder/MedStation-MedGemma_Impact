"""
Agent API endpoints

Route handlers for all agent-related operations including:
- Task execution
- Status monitoring
- Multi-agent coordination
- Custom tools
- Performance metrics
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import AGENT_EXECUTION_RATE_LIMIT
from ..services.agent import AgentExecutor, ToolRegistry
from ..services.agent.agent_types import AGENT_PROFILES, AgentRole
from ..services.agent.coordinator import CoordinationStrategy, get_coordinator
from ..services.agent.custom_tools import (
    CustomToolDefinition,
    ToolParameter,
    ToolType,
    get_custom_tool_registry,
)
from ..services.agent.feedback import FeedbackType, TaskFeedback, get_feedback_store
from .models import (
    AgentStatusResponse,
    AgentTaskRequest,
    CustomToolRequest,
    FeedbackRequest,
    MultiAgentRequest,
)
from .state import get_active_agent, get_active_agents_count, store_active_agent

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


# ===== Core Endpoints =====


@router.post("/execute")
@limiter.limit(AGENT_EXECUTION_RATE_LIMIT)
async def execute_agent_task(request: AgentTaskRequest, http_request: Request) -> StreamingResponse:
    """
    Execute a task autonomously with an agent.

    **Rate Limit:** 5 requests per minute per IP address

    The agent will:
    1. Analyze the task and create a plan
    2. Execute each step using available tools
    3. Stream progress updates in real-time
    4. Adapt plan based on results

    **SSE Event Format:**
    ```
    data: {"type": "planning", "status": "planning", "data": {...}}

    data: {"type": "plan_created", "status": "executing", "data": {...}}

    data: {"type": "step_complete", "status": "executing", "data": {...}}
    ```

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/agent/execute \
      -H "Content-Type: application/json" \
      -d '{
        "task": "Fix the authentication bug in login.py",
        "workspace_path": "/path/to/project",
        "auto_approve": false
      }'
    ```
    """
    # Create task ID
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # Build workspace context
    workspace_context: dict[str, Any] = {}
    if request.recent_files:
        workspace_context["recent_files"] = request.recent_files
    if request.current_errors:
        workspace_context["current_errors"] = request.current_errors

    # Create agent executor with Ollama client
    from ..services.ollama_client import get_ollama_client

    agent = AgentExecutor(
        workspace_root=request.workspace_path, llm_client=get_ollama_client(), max_iterations=20
    )

    # Store agent
    store_active_agent(task_id, agent)

    async def stream_events():
        """Stream agent execution events"""
        try:
            # Start execution
            async for event in agent.execute_task(
                task_request=request.task,
                workspace_context=workspace_context,
                auto_approve=request.auto_approve,
            ):
                # Add task_id to event
                event["task_id"] = task_id

                # Format as SSE
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            error_event = {
                "type": "error",
                "task_id": task_id,
                "data": {"message": f"Execution failed: {e!s}"},
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        finally:
            # Send final event
            final_event = {
                "type": "done",
                "task_id": task_id,
                "data": {"status": agent.status.value},
            }
            yield f"data: {json.dumps(final_event)}\n\n"

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Task-ID": task_id,
        },
    )


@router.get("/status/{task_id}", response_model=AgentStatusResponse)
async def get_agent_status(task_id: str) -> AgentStatusResponse:
    """
    Get the status of a running or completed agent task.

    Returns current plan, progress, and execution log.
    """
    agent = get_active_agent(task_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    status = agent.get_status()

    return AgentStatusResponse(
        task_id=task_id,
        status=status["status"],
        current_plan=status.get("current_plan"),
        execution_log=status.get("execution_log"),
    )


@router.post("/cancel/{task_id}")
async def cancel_agent_task(task_id: str) -> dict[str, str]:
    """
    Cancel a running agent task.

    Stops execution at the current step.
    """
    agent = get_active_agent(task_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    await agent.cancel()

    return {"task_id": task_id, "status": "cancelled", "message": "Task cancelled successfully"}


@router.get("/tools")
async def list_agent_tools(
    workspace_path: str = Query(..., description="Workspace path"),
) -> dict[str, list[dict] | int]:
    """
    List available tools for agent execution.

    Returns JSON schemas for all tools.
    """
    registry = ToolRegistry(workspace_root=workspace_path)
    tools = registry.get_schemas()

    return {"tools": tools, "count": len(tools)}


@router.get("/health")
async def agent_health() -> dict[str, str | int | list[str]]:
    """Health check for agent service"""
    return {
        "status": "healthy",
        "active_tasks": get_active_agents_count(),
        "capabilities": [
            "task_planning",
            "multi_step_execution",
            "tool_calling",
            "code_editing",
            "multi_agent_collaboration",
            "custom_tools",
            "performance_tracking",
        ],
    }


# ===== Advanced Features =====


@router.post("/multi/execute")
async def execute_multi_agent(request: MultiAgentRequest) -> StreamingResponse:
    """
    Execute a task using multiple collaborating agents

    Different agents specialize in different tasks:
    - CodeAgent: Writing and editing code
    - TestAgent: Writing and running tests
    - DebugAgent: Finding and fixing bugs
    - ReviewAgent: Code review and quality
    - ResearchAgent: Documentation and analysis

    Coordination strategies:
    - sequential: Agents work one after another
    - parallel: Agents work simultaneously
    - pipeline: Output of one feeds into next
    - collaborative: Agents work together with shared context

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/agent/multi/execute \
      -H "Content-Type: application/json" \
      -d '{
        "task": "Implement user authentication with tests",
        "workspace_path": "/path/to/project",
        "strategy": "sequential"
      }'
    ```
    """
    # Parse strategy
    try:
        strategy = CoordinationStrategy(request.strategy)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid strategy. Must be one of: sequential, parallel, pipeline, collaborative",
        )

    # Get coordinator
    coordinator = get_coordinator()

    async def stream_events():
        """Stream multi-agent execution events"""
        try:
            async for event in coordinator.execute_collaborative_task(
                task_description=request.task,
                workspace_path=request.workspace_path,
                strategy=strategy,
                auto_approve=request.auto_approve,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            error_event = {"type": "error", "data": {"message": str(e)}}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents() -> dict[str, list[dict] | int]:
    """
    List available agent types and their capabilities

    Returns information about all specialized agents.
    """
    agents = []
    for role, profile in AGENT_PROFILES.items():
        agents.append(
            {
                "role": role.value,
                "name": profile.name,
                "description": profile.description,
                "capabilities": [
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "confidence": cap.confidence_level,
                    }
                    for cap in profile.capabilities
                ],
                "specializations": profile.specializations,
                "available_tools": list(profile.available_tools),
            }
        )

    return {"agents": agents, "count": len(agents)}


@router.get("/metrics/{agent_role}")
async def get_agent_metrics(agent_role: str) -> dict[str, str | dict]:
    """
    Get performance metrics for a specific agent

    Returns:
    - Total tasks executed
    - Success/failure rates
    - Average rating from user feedback
    - Most used tools
    - Common patterns
    """
    # Validate agent role
    try:
        AgentRole(agent_role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent role. Must be one of: {[r.value for r in AgentRole]}",
        )

    feedback_store = get_feedback_store()

    # Get metrics
    metrics = feedback_store.get_agent_metrics(agent_role)

    # Get patterns
    patterns = feedback_store.get_task_patterns(agent_role)

    return {
        "agent_role": agent_role,
        "metrics": {
            "total_tasks": metrics.total_tasks,
            "successful_tasks": metrics.successful_tasks,
            "failed_tasks": metrics.failed_tasks,
            "partial_tasks": metrics.partial_tasks,
            "success_rate": metrics.success_rate,
            "average_rating": metrics.average_rating,
            "average_duration_seconds": metrics.average_duration,
            "total_steps_completed": metrics.total_steps_completed,
            "most_used_tools": metrics.most_used_tools,
        },
        "patterns": patterns,
    }


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest) -> dict[str, bool | str]:
    """
    Submit feedback on a completed task

    Feedback helps improve agent performance over time.

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/agent/feedback \
      -H "Content-Type: application/json" \
      -d '{
        "task_id": "task_abc123",
        "agent_role": "code",
        "feedback_type": "positive",
        "rating": 5,
        "comment": "Great implementation!"
      }'
    ```
    """
    # Validate feedback type
    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid feedback type. Must be: positive, negative, or neutral"
        )

    # Create and store feedback
    feedback = TaskFeedback(
        task_id=request.task_id,
        agent_role=request.agent_role,
        feedback_type=feedback_type,
        rating=request.rating,
        comment=request.comment,
    )

    feedback_store = get_feedback_store()
    feedback_store.record_feedback(feedback)

    return {
        "success": True,
        "message": "Feedback recorded successfully",
        "feedback_id": feedback.task_id,
    }


# ===== Custom Tools Endpoints =====


@router.post("/tools/custom")
async def register_custom_tool(request: CustomToolRequest) -> dict[str, bool | str | dict]:
    """
    Register a custom tool

    Allows creating custom tools with:
    - Python functions
    - Shell scripts
    - API calls

    **Example Python Tool:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/agent/tools/custom \
      -H "Content-Type: application/json" \
      -d '{
        "name": "format_json",
        "description": "Format JSON data",
        "tool_type": "python_function",
        "parameters": [
          {"name": "data", "type": "string", "description": "JSON to format", "required": true}
        ],
        "implementation": "import json\\n\\ndef format_json(data: str) -> str:\\n    return json.dumps(json.loads(data), indent=2)",
        "category": "formatting"
      }'
    ```
    """
    # Validate tool type
    try:
        tool_type = ToolType(request.tool_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid tool type. Must be: python_function, shell_script, or api_call",
        )

    # Create tool definition
    tool_def = CustomToolDefinition(
        name=request.name,
        description=request.description,
        tool_type=tool_type,
        parameters=[ToolParameter(**p) for p in request.parameters],
        implementation=request.implementation,
        category=request.category,
        tags=request.tags,
    )

    # Register tool
    registry = get_custom_tool_registry()
    success = registry.register_tool(tool_def)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to register tool")

    return {
        "success": True,
        "message": f"Tool '{request.name}' registered successfully",
        "tool": tool_def.to_dict(),
    }


@router.get("/tools/custom")
async def list_custom_tools(
    category: str | None = Query(None, description="Filter by category"),
    tool_type: str | None = Query(None, description="Filter by type"),
) -> dict[str, list[dict] | int]:
    """
    List all custom tools

    Optionally filter by category or type.
    """
    registry = get_custom_tool_registry()

    # Parse tool type if provided
    type_filter = None
    if tool_type:
        try:
            type_filter = ToolType(tool_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tool type")

    tools = registry.list_tools(category=category, tool_type=type_filter)

    return {"tools": [tool.to_dict() for tool in tools], "count": len(tools)}


@router.delete("/tools/custom/{tool_name}")
async def unregister_custom_tool(tool_name: str) -> dict[str, bool | str]:
    """
    Unregister a custom tool

    Removes the tool from the registry.
    """
    registry = get_custom_tool_registry()
    success = registry.unregister_tool(tool_name)

    if not success:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    return {"success": True, "message": f"Tool '{tool_name}' unregistered successfully"}


@router.post("/tools/custom/{tool_name}/execute")
async def execute_custom_tool(
    tool_name: str, parameters: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    """
    Execute a custom tool

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v1/agent/tools/custom/format_json/execute \
      -H "Content-Type: application/json" \
      -d '{"data": "{\\"key\\":\\"value\\"}"}'
    ```
    """
    registry = get_custom_tool_registry()

    try:
        result: dict[str, Any] = registry.execute_tool(tool_name, **parameters)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
