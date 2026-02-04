"""
Unified Orchestrator

Main orchestration engine that ties together all components.
Provides the primary interface for agent orchestration.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator

from .coordinator import ExecutionCoordinator
from .interface import (
    Orchestrator,
    OrchestrationRequest,
    OrchestrationResult,
    ExecutionStatus,
)
from .router import IntentBasedRouter, create_router

logger = logging.getLogger(__name__)


class MagnetarOrchestrator(Orchestrator):
    """
    Main orchestration engine for MagnetarCode.

    Integrates:
    - Intent classification (Phase 2)
    - Recursive task planning (Phase 3)
    - Agentic execution loop (Phase 4)
    - Aider integration (Phase 5)
    - Continue integration (Phase 6)

    Features:
    - Intelligent request routing
    - Multi-agent coordination
    - Streaming responses
    - Execution tracking
    - Graceful error handling
    """

    def __init__(
        self,
        workspace_root: str = "",
        aider_bridge=None,
        continue_bridge=None,
        use_ml_routing: bool = True,
    ):
        """
        Initialize orchestrator.

        Args:
            workspace_root: Default workspace directory
            aider_bridge: Aider bridge for code editing
            continue_bridge: Continue bridge for IDE features
            use_ml_routing: Whether to use ML-based intent routing
        """
        self._workspace_root = workspace_root
        self._aider_bridge = aider_bridge
        self._continue_bridge = continue_bridge

        # Initialize components
        self._router = create_router(use_ml=use_ml_routing)
        self._coordinator = ExecutionCoordinator(
            aider_bridge=aider_bridge,
            continue_bridge=continue_bridge,
        )

        # Result storage
        self._results: dict[str, OrchestrationResult] = {}

        logger.info(
            f"MagnetarOrchestrator initialized "
            f"(ml_routing={use_ml_routing}, "
            f"aider={'enabled' if aider_bridge else 'disabled'}, "
            f"continue={'enabled' if continue_bridge else 'disabled'})"
        )

    async def process(
        self,
        request: OrchestrationRequest,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Process an orchestration request.

        This is the main entry point for all user requests.

        Args:
            request: The request to process

        Yields:
            Execution events (progress, responses, errors)
        """
        # Ensure request has ID
        if not request.request_id:
            request.request_id = str(uuid.uuid4())

        # Set workspace if not provided
        if not request.workspace_root and self._workspace_root:
            request.workspace_root = self._workspace_root

        logger.info(
            f"Processing request {request.request_id}: "
            f"{request.user_input[:50]}..."
        )

        yield {
            "type": "request_received",
            "request_id": request.request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Route the request
            yield {"type": "routing", "status": "started"}

            routing = await self._router.route(request)

            yield {
                "type": "routing",
                "status": "complete",
                "decision": {
                    "primary_agent": routing.primary_agent.value,
                    "secondary_agents": [a.value for a in routing.secondary_agents],
                    "confidence": routing.confidence,
                    "rationale": routing.rationale,
                    "requires_planning": routing.requires_planning,
                },
            }

            # Execute via coordinator
            async for event in self._coordinator.coordinate(request, routing):
                yield event

            # Get and store result
            result = self._coordinator.get_result(request.request_id)
            if result:
                self._results[request.request_id] = result

            yield {
                "type": "request_complete",
                "request_id": request.request_id,
                "status": result.status.value if result else "unknown",
            }

        except Exception as e:
            logger.exception(f"Orchestration error: {e}")

            error_result = OrchestrationResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                response="",
                error=str(e),
                error_type=type(e).__name__,
            )
            self._results[request.request_id] = error_result

            yield {
                "type": "error",
                "request_id": request.request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def get_result(
        self,
        request_id: str,
    ) -> OrchestrationResult | None:
        """Get the final result of a request"""
        # Check coordinator first (for in-progress)
        result = self._coordinator.get_result(request_id)
        if result:
            return result

        # Check stored results
        return self._results.get(request_id)

    async def cancel(self, request_id: str) -> bool:
        """Cancel a request"""
        return await self._coordinator.cancel(request_id)

    def get_capabilities(self) -> dict[str, Any]:
        """Get orchestrator capabilities"""
        return {
            "agents": [
                {
                    "type": cap.agent_type.value,
                    "name": cap.name,
                    "description": cap.description,
                    "can_write_files": cap.can_write_files,
                    "can_execute_commands": cap.can_execute_commands,
                }
                for cap in self._router.get_available_agents()
            ],
            "features": {
                "ml_routing": isinstance(self._router, IntentBasedRouter),
                "aider_integration": self._aider_bridge is not None,
                "continue_integration": self._continue_bridge is not None,
                "streaming": True,
                "cancellation": True,
            },
            "stats": self._coordinator.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "total_requests": len(self._results),
            "coordinator": self._coordinator.get_stats(),
            "results_by_status": self._count_results_by_status(),
        }

    def _count_results_by_status(self) -> dict[str, int]:
        """Count results by status"""
        counts: dict[str, int] = {}
        for result in self._results.values():
            status = result.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts


def create_orchestrator(
    workspace_root: str = "",
    enable_aider: bool = True,
    enable_continue: bool = True,
    use_ml_routing: bool = True,
) -> MagnetarOrchestrator:
    """
    Create configured orchestrator.

    Args:
        workspace_root: Default workspace directory
        enable_aider: Whether to enable Aider integration
        enable_continue: Whether to enable Continue integration
        use_ml_routing: Whether to use ML-based routing

    Returns:
        Configured MagnetarOrchestrator
    """
    aider_bridge = None
    continue_bridge = None

    if enable_aider:
        try:
            from ..aider import AiderConfig, create_aider_bridge

            config = AiderConfig(workspace_root=workspace_root)
            aider_bridge = create_aider_bridge(config)
            logger.info("Aider integration enabled")
        except ImportError:
            logger.warning("Aider module not available")
        except Exception as e:
            logger.warning(f"Failed to initialize Aider: {e}")

    if enable_continue:
        try:
            from ..continue_ext import create_continue_bridge

            continue_bridge = create_continue_bridge(
                workspace_root=workspace_root,
                aider_bridge=aider_bridge,
            )
            logger.info("Continue integration enabled")
        except ImportError:
            logger.warning("Continue module not available")
        except Exception as e:
            logger.warning(f"Failed to initialize Continue: {e}")

    return MagnetarOrchestrator(
        workspace_root=workspace_root,
        aider_bridge=aider_bridge,
        continue_bridge=continue_bridge,
        use_ml_routing=use_ml_routing,
    )


# Convenience function for quick usage
async def orchestrate(
    user_input: str,
    workspace_root: str = "",
    session_id: str = "",
    **kwargs,
) -> AsyncIterator[dict[str, Any]]:
    """
    Quick orchestration helper.

    Args:
        user_input: The user's request
        workspace_root: Workspace directory
        session_id: Session ID for context
        **kwargs: Additional request parameters

    Yields:
        Execution events
    """
    orchestrator = create_orchestrator(workspace_root=workspace_root)

    request = OrchestrationRequest(
        request_id=str(uuid.uuid4()),
        session_id=session_id or str(uuid.uuid4()),
        user_input=user_input,
        workspace_root=workspace_root,
        **kwargs,
    )

    async for event in orchestrator.process(request):
        yield event
