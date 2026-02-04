"""
Agent Router

Routes requests to appropriate agents based on intent classification.
Integrates with the NLP intent system from Phase 2.
"""

import logging
from typing import Any

from ..intent import IntentResult, IntentType, get_intent_classifier
from .interface import (
    AgentCapabilities,
    AgentType,
    OrchestrationRequest,
    Router,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


# Mapping from intent types to agent types
INTENT_TO_AGENT: dict[IntentType, AgentType] = {
    IntentType.CODE_EDIT: AgentType.EDIT,
    IntentType.CODE_EXPLAIN: AgentType.ANALYZE,
    IntentType.CODE_REVIEW: AgentType.ANALYZE,
    IntentType.CODE_GENERATE: AgentType.EDIT,
    IntentType.DEBUG: AgentType.DEBUG,
    IntentType.TEST: AgentType.TEST,
    IntentType.REFACTOR: AgentType.REFACTOR,
    IntentType.DOCUMENTATION: AgentType.EDIT,
    IntentType.SEARCH: AgentType.ANALYZE,
    IntentType.QUESTION: AgentType.CHAT,
    IntentType.COMMAND: AgentType.EXECUTE,
    IntentType.PLANNING: AgentType.PLAN,
    IntentType.UNKNOWN: AgentType.CHAT,
}


# Agent capabilities registry
AGENT_CAPABILITIES: dict[AgentType, AgentCapabilities] = {
    AgentType.CHAT: AgentCapabilities(
        agent_type=AgentType.CHAT,
        name="Chat Agent",
        description="General Q&A and conversation",
        can_read_files=True,
        can_write_files=False,
        can_search_codebase=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=500,
    ),
    AgentType.EDIT: AgentCapabilities(
        agent_type=AgentType.EDIT,
        name="Edit Agent",
        description="Code editing and generation via Aider",
        can_read_files=True,
        can_write_files=True,
        can_search_codebase=True,
        can_use_tools=True,
        preferred_model="qwen2.5-coder:32b",
        typical_latency_ms=5000,
    ),
    AgentType.ANALYZE: AgentCapabilities(
        agent_type=AgentType.ANALYZE,
        name="Analyze Agent",
        description="Code analysis and explanation",
        can_read_files=True,
        can_write_files=False,
        can_search_codebase=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=2000,
    ),
    AgentType.PLAN: AgentCapabilities(
        agent_type=AgentType.PLAN,
        name="Planning Agent",
        description="Task decomposition and planning",
        can_read_files=True,
        can_write_files=False,
        can_search_codebase=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=3000,
    ),
    AgentType.EXECUTE: AgentCapabilities(
        agent_type=AgentType.EXECUTE,
        name="Execution Agent",
        description="Command and tool execution",
        can_read_files=True,
        can_write_files=True,
        can_execute_commands=True,
        can_use_tools=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=2000,
    ),
    AgentType.DEBUG: AgentCapabilities(
        agent_type=AgentType.DEBUG,
        name="Debug Agent",
        description="Debugging and error analysis",
        can_read_files=True,
        can_write_files=False,
        can_execute_commands=True,
        can_search_codebase=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=3000,
    ),
    AgentType.TEST: AgentCapabilities(
        agent_type=AgentType.TEST,
        name="Test Agent",
        description="Test generation and execution",
        can_read_files=True,
        can_write_files=True,
        can_execute_commands=True,
        preferred_model="qwen2.5-coder:7b",
        typical_latency_ms=5000,
    ),
    AgentType.REFACTOR: AgentCapabilities(
        agent_type=AgentType.REFACTOR,
        name="Refactor Agent",
        description="Code refactoring",
        can_read_files=True,
        can_write_files=True,
        can_search_codebase=True,
        can_use_tools=True,
        preferred_model="qwen2.5-coder:32b",
        typical_latency_ms=5000,
    ),
}


class IntentBasedRouter(Router):
    """
    Routes requests based on NLP intent classification.

    Uses the hybrid intent classifier from Phase 2 to determine
    which agent(s) should handle a request.
    """

    def __init__(self, use_transformer: bool = True):
        """
        Initialize intent-based router.

        Args:
            use_transformer: Whether to use transformer-based classification
        """
        self._classifier = get_intent_classifier(use_transformer=use_transformer)
        self._routing_rules = self._init_routing_rules()

    def _init_routing_rules(self) -> dict[str, Any]:
        """Initialize additional routing rules"""
        return {
            # Complex tasks that need planning
            "planning_triggers": [
                "implement",
                "build",
                "create feature",
                "add functionality",
                "refactor entire",
                "redesign",
            ],
            # Tasks that need file context
            "context_triggers": [
                "this file",
                "this function",
                "this class",
                "selected code",
                "current file",
            ],
            # Multi-agent tasks
            "multi_agent_patterns": {
                "write tests for": [AgentType.ANALYZE, AgentType.TEST],
                "refactor and test": [AgentType.REFACTOR, AgentType.TEST],
                "debug and fix": [AgentType.DEBUG, AgentType.EDIT],
                "analyze and improve": [AgentType.ANALYZE, AgentType.REFACTOR],
            },
        }

    async def route(
        self,
        request: OrchestrationRequest,
    ) -> RoutingDecision:
        """
        Route request to appropriate agent(s).

        Uses intent classification + heuristics for routing.
        """
        user_input = request.user_input.lower()

        # Classify intent
        intent_result = await self._classify_intent(request.user_input)

        # Map to primary agent
        primary_agent = INTENT_TO_AGENT.get(
            intent_result.primary_intent, AgentType.CHAT
        )

        # Check for multi-agent patterns
        secondary_agents = self._check_multi_agent(user_input)

        # Check if planning is needed
        requires_planning = self._check_planning_needed(
            user_input, intent_result
        )

        # Check if context is needed
        requires_context = self._check_context_needed(user_input, request)

        # Estimate complexity
        estimated_steps = self._estimate_steps(
            intent_result, requires_planning
        )

        return RoutingDecision(
            primary_agent=primary_agent,
            secondary_agents=secondary_agents,
            confidence=intent_result.confidence,
            rationale=self._build_rationale(intent_result, primary_agent),
            requires_planning=requires_planning,
            requires_context=requires_context,
            estimated_steps=estimated_steps,
        )

    async def _classify_intent(self, text: str) -> IntentResult:
        """Classify user intent"""
        try:
            return await self._classifier.classify(text)
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return IntentResult(
                intent_type=IntentType.UNKNOWN,
                confidence=0.3,
                reasoning="Classification failed",
            )

    def _check_multi_agent(self, text: str) -> list[AgentType]:
        """Check if multiple agents are needed"""
        secondary = []

        for pattern, agents in self._routing_rules["multi_agent_patterns"].items():
            if pattern in text:
                secondary.extend(agents)

        return list(set(secondary))  # Deduplicate

    def _check_planning_needed(
        self, text: str, intent: IntentResult
    ) -> bool:
        """Check if task planning is needed"""
        # Explicit planning intent
        if intent.primary_intent == IntentType.PLANNING:
            return True

        # Complex task triggers
        for trigger in self._routing_rules["planning_triggers"]:
            if trigger in text:
                return True

        # High-complexity intents
        if intent.primary_intent in (
            IntentType.REFACTOR,
            IntentType.CODE_GENERATE,
        ):
            # Check for scope indicators
            if any(w in text for w in ["entire", "all", "whole", "complete"]):
                return True

        return False

    def _check_context_needed(
        self, text: str, request: OrchestrationRequest
    ) -> bool:
        """Check if file/codebase context is needed"""
        # Always need context if there's selected code
        if request.selected_code:
            return True

        # Always need context if active file
        if request.active_file:
            return True

        # Check for context triggers
        for trigger in self._routing_rules["context_triggers"]:
            if trigger in text:
                return True

        return True  # Default to including context

    def _estimate_steps(
        self, intent: IntentResult, requires_planning: bool
    ) -> int:
        """Estimate number of execution steps"""
        base_steps = {
            IntentType.QUESTION: 1,
            IntentType.SEARCH: 1,
            IntentType.CODE_EXPLAIN: 2,
            IntentType.CODE_EDIT: 3,
            IntentType.CODE_GENERATE: 4,
            IntentType.DEBUG: 4,
            IntentType.TEST: 5,
            IntentType.REFACTOR: 5,
            IntentType.PLANNING: 2,
        }

        steps = base_steps.get(intent.primary_intent, 2)

        if requires_planning:
            steps += 2  # Planning adds steps

        return steps

    def _build_rationale(
        self, intent: IntentResult, agent: AgentType
    ) -> str:
        """Build routing rationale"""
        return (
            f"Classified as {intent.primary_intent.value} "
            f"(confidence: {intent.confidence:.0%}), "
            f"routing to {agent.value} agent"
        )

    def get_available_agents(self) -> list[AgentCapabilities]:
        """Get all available agent capabilities"""
        return list(AGENT_CAPABILITIES.values())


class RuleBasedRouter(Router):
    """
    Simple rule-based router.

    Uses pattern matching for routing decisions.
    Faster but less accurate than intent-based routing.
    """

    def __init__(self):
        self._patterns = self._init_patterns()

    def _init_patterns(self) -> dict[AgentType, list[str]]:
        """Initialize routing patterns"""
        return {
            AgentType.EDIT: [
                "edit", "change", "modify", "update", "fix",
                "add", "remove", "create", "write", "implement",
            ],
            AgentType.ANALYZE: [
                "explain", "what does", "how does", "understand",
                "analyze", "review", "describe", "show me",
            ],
            AgentType.DEBUG: [
                "debug", "error", "bug", "issue", "problem",
                "not working", "fails", "broken", "crash",
            ],
            AgentType.TEST: [
                "test", "tests", "testing", "coverage",
                "unit test", "integration test",
            ],
            AgentType.REFACTOR: [
                "refactor", "restructure", "reorganize",
                "clean up", "improve", "optimize",
            ],
            AgentType.PLAN: [
                "plan", "design", "architect", "strategy",
                "approach", "how should", "steps to",
            ],
        }

    async def route(
        self,
        request: OrchestrationRequest,
    ) -> RoutingDecision:
        """Route using pattern matching"""
        text = request.user_input.lower()

        # Find matching patterns
        matches: dict[AgentType, int] = {}
        for agent_type, patterns in self._patterns.items():
            count = sum(1 for p in patterns if p in text)
            if count > 0:
                matches[agent_type] = count

        if matches:
            # Use agent with most matches
            primary = max(matches, key=matches.get)
            confidence = min(0.9, 0.5 + matches[primary] * 0.1)
        else:
            # Default to chat
            primary = AgentType.CHAT
            confidence = 0.5

        return RoutingDecision(
            primary_agent=primary,
            confidence=confidence,
            rationale=f"Pattern matched to {primary.value}",
        )

    def get_available_agents(self) -> list[AgentCapabilities]:
        """Get available agents"""
        return list(AGENT_CAPABILITIES.values())


def create_router(use_ml: bool = True) -> Router:
    """
    Create appropriate router.

    Args:
        use_ml: Whether to use ML-based intent classification

    Returns:
        Configured router
    """
    if use_ml:
        return IntentBasedRouter(use_transformer=True)
    else:
        return RuleBasedRouter()
