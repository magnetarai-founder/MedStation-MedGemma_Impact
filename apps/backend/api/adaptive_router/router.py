#!/usr/bin/env python3
"""
Adaptive Router with Learning Integration for MedStation
Combines enhanced routing with learning system for intelligent, adaptive behavior
Ported from Jarvis Agent with MedStation-specific adaptations

Module structure (P2 decomposition):
- adaptive_router_patterns.py: Enums, dataclasses, and DEFAULT_ROUTE_PATTERNS
- adaptive_router.py: EnhancedRouter and AdaptiveRouter classes (this file)
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# Import from extracted module (P2 decomposition)
from api.adaptive_router.patterns import (
    TaskType,
    ToolType,
    RoutePattern,
    RouteResult,
    DEFAULT_ROUTE_PATTERNS,
)

# Local imports
from api.learning_system import LearningSystem, Recommendation
from api.jarvis_memory import JarvisMemory


@dataclass
class AdaptiveRouteResult(RouteResult):
    """Extended route result with learning insights"""
    recommendations: List[Recommendation] = None
    adjusted_confidence: float = 0.0
    learning_insights: Dict[str, Any] = None


# ===== Enhanced Router =====

class EnhancedRouter:
    """Advanced task router with pattern matching and confidence scoring"""

    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.regex_cache = {}
        self._compile_regex_patterns()

    def _initialize_patterns(self) -> List[RoutePattern]:
        """Initialize comprehensive routing patterns for MedStation.

        Returns DEFAULT_ROUTE_PATTERNS from extracted module (P2 decomposition).
        """
        return DEFAULT_ROUTE_PATTERNS

    def _compile_regex_patterns(self) -> None:
        """Pre-compile regex patterns for performance"""
        for pattern in self.patterns:
            if pattern.pattern_type == 'regex':
                for regex_str in pattern.patterns:
                    if regex_str not in self.regex_cache:
                        try:
                            self.regex_cache[regex_str] = re.compile(regex_str, re.IGNORECASE)
                        except re.error:
                            self.regex_cache[regex_str] = None

    def _calculate_pattern_confidence(self, command: str, pattern: RoutePattern) -> Tuple[float, List[str]]:
        """Calculate confidence score for a pattern match"""
        confidence = 0.0
        matched = []
        command_lower = command.lower()

        if pattern.pattern_type == 'keyword':
            for keyword in pattern.patterns:
                if keyword.lower() in command_lower:
                    if keyword.lower() == command_lower.strip():
                        confidence = 1.0
                    else:
                        confidence = max(confidence, 0.7)
                    matched.append(keyword)

        elif pattern.pattern_type == 'regex':
            for regex_str in pattern.patterns:
                regex = self.regex_cache.get(regex_str)
                if regex and regex.search(command):
                    match = regex.search(command)
                    match_length = len(match.group(0))
                    command_length = len(command)
                    match_ratio = match_length / command_length if command_length > 0 else 0
                    confidence = max(confidence, 0.5 + (match_ratio * 0.5))
                    matched.append(regex_str)

        # Apply context hints
        for hint in pattern.context_hints:
            if hint.lower() in command_lower:
                confidence = min(1.0, confidence + 0.1)

        # Apply negative patterns
        for neg_pattern in pattern.negative_patterns:
            if neg_pattern.lower() in command_lower:
                confidence = max(0, confidence - 0.3)

        # Apply weight
        confidence *= pattern.weight

        return confidence, matched

    def route_task(self, command: str) -> RouteResult:
        """Route a task with confidence scoring"""
        results = []

        for pattern in self.patterns:
            confidence, matched = self._calculate_pattern_confidence(command, pattern)

            if confidence >= pattern.min_confidence:
                results.append((
                    pattern.task_type,
                    pattern.tool_type,
                    confidence,
                    matched,
                    pattern
                ))

        results.sort(key=lambda x: x[2], reverse=True)

        if results:
            best = results[0]
            task_type, tool_type, confidence, matched, pattern = best

            fallbacks = []
            for r in results[1:4]:
                if r[2] > 0.4:
                    fallbacks.append((r[0], r[1], r[2]))

            reasoning = self._generate_reasoning(command, matched, confidence, pattern)

            return RouteResult(
                task_type=task_type,
                tool_type=tool_type,
                confidence=confidence,
                matched_patterns=matched,
                reasoning=reasoning,
                fallback_options=fallbacks,
                context={}
            )

        # Default fallback to Ollama chat
        return RouteResult(
            task_type=TaskType.CHAT,
            tool_type=ToolType.OLLAMA,
            confidence=0.3,
            matched_patterns=[],
            reasoning="No strong pattern match, defaulting to general chat",
            fallback_options=[],
            context={}
        )

    def _generate_reasoning(self, command: str, matched: List[str], confidence: float, pattern: RoutePattern) -> str:
        """Generate human-readable reasoning for the routing decision"""
        parts = []

        if confidence > 0.8:
            parts.append(f"High confidence ({confidence:.1%})")
        elif confidence > 0.6:
            parts.append(f"Good match ({confidence:.1%})")
        else:
            parts.append(f"Partial match ({confidence:.1%})")

        if matched:
            parts.append(f"Pattern detected")

        parts.append(f"→ {pattern.tool_type.value}")

        return " - ".join(parts)


# ===== Adaptive Router =====

class AdaptiveRouter:
    """
    Intelligent adaptive router that:
    - Uses enhanced pattern matching
    - Learns from execution history
    - Adapts to user preferences
    - Provides context-aware recommendations
    """

    def __init__(self, memory: JarvisMemory = None, learning: LearningSystem = None):
        self.base_router = EnhancedRouter()
        self.memory = memory or JarvisMemory()
        self.learning = learning or LearningSystem(memory=self.memory)
        self.routing_history = []

    def route_task(self, command: str, context: Dict = None) -> AdaptiveRouteResult:
        """Route task with adaptive learning"""

        # Get base routing result
        base_result = self.base_router.route_task(command)

        # Get project context if not provided
        if not context:
            context = {}
            try:
                project_context = self.learning.detect_project_context()
                context['project'] = project_context
            except (AttributeError, OSError):
                pass  # Context detection not available

        # Get learning recommendations
        recommendations = self.learning.get_recommendations(command, context)

        # Adjust confidence based on historical success
        adjusted_confidence = self._adjust_confidence(
            command,
            base_result.task_type,
            base_result.tool_type,
            base_result.confidence
        )

        # Check for user preference overrides
        override_result = self._check_preference_override(command, base_result)
        if override_result:
            base_result = override_result

        # Get similar successful commands
        similar_commands = self.memory.find_similar_commands(command, limit=3)

        # Build learning insights
        project_type = 'unknown'
        if 'project' in context and hasattr(context['project'], 'project_type'):
            project_type = context['project'].project_type

        insights = {
            'similar_commands': similar_commands,
            'success_rate': self.learning.get_success_rate(
                command,
                base_result.tool_type.value
            ),
            'user_preferences': self.learning.get_preferences('tool'),
            'project_type': project_type
        }

        # Create adaptive result
        result = AdaptiveRouteResult(
            task_type=base_result.task_type,
            tool_type=base_result.tool_type,
            confidence=base_result.confidence,
            matched_patterns=base_result.matched_patterns,
            reasoning=base_result.reasoning,
            fallback_options=base_result.fallback_options,
            recommendations=recommendations,
            adjusted_confidence=adjusted_confidence,
            learning_insights=insights,
            suggested_model=base_result.suggested_model,
            context=context
        )

        # Store routing decision
        self._store_routing_decision(command, result)

        return result

    def _adjust_confidence(self, command: str, task_type: TaskType,
                          tool_type: ToolType, base_confidence: float) -> float:
        """Adjust confidence based on historical success"""

        success_rate = self.learning.get_success_rate(command, tool_type.value)

        if success_rate > 0 and success_rate != 0.5:
            # Blend base confidence with historical success
            adjusted = (base_confidence * 0.6) + (success_rate * 0.4)
            return min(1.0, adjusted)

        return base_confidence

    def _check_preference_override(self, command: str,
                                   base_result: RouteResult) -> Optional[RouteResult]:
        """Check if user preferences should override routing"""

        tool_prefs = self.learning.get_preferences('tool')

        if tool_prefs:
            top_pref = tool_prefs[0]

            # Strong preference + low confidence = override
            if top_pref.confidence > 0.8 and base_result.confidence < 0.7:
                tool_map = {
                    'ollama': ToolType.OLLAMA,
                    'system': ToolType.SYSTEM,
                    'p2p': ToolType.P2P,
                    'data': ToolType.DATA
                }

                if top_pref.preference in tool_map:
                    preferred_tool = tool_map[top_pref.preference]

                    return RouteResult(
                        task_type=base_result.task_type,
                        tool_type=preferred_tool,
                        confidence=top_pref.confidence,
                        matched_patterns=['user_preference'],
                        reasoning=f"User preference: {top_pref.preference} ({top_pref.confidence:.0%})",
                        fallback_options=[(base_result.task_type, base_result.tool_type, base_result.confidence)],
                        context={}
                    )

        return None

    def _store_routing_decision(self, command: str, result: AdaptiveRouteResult) -> None:
        """Store routing decision for future learning"""

        self.routing_history.append({
            'command': command,
            'task_type': result.task_type.value,
            'tool_type': result.tool_type.value,
            'confidence': result.confidence,
            'adjusted_confidence': result.adjusted_confidence,
            'timestamp': Path.cwd().stat().st_mtime
        })

        if len(self.routing_history) > 100:
            self.routing_history = self.routing_history[-100:]

    def record_execution_result(self, command: str, tool: str,
                               success: bool, execution_time: float) -> None:
        """Record execution result for learning"""

        # Track in learning system
        self.learning.track_execution(command, tool, success, execution_time)

        # Find task type from history
        task_type = None
        for entry in self.routing_history:
            if entry['command'] == command:
                task_type = entry['task_type']
                break

        # Store in memory
        self.memory.store_command(
            command,
            task_type or 'unknown',
            tool,
            success,
            execution_time
        )

    def route(self, command: str) -> Dict[str, Any]:
        """Simple route interface for compatibility"""
        result = self.route_task(command)
        return {
            'task_type': result.task_type.value if result.task_type else 'unknown',
            'tool': result.tool_type.value if result.tool_type else 'ollama',
            'confidence': result.confidence,
            'model': result.suggested_model,
            'context': result.context or {}
        }

    def record_feedback(self, command: str, task_type: str, tool: str,
                        success: bool, execution_time: float) -> None:
        """Record feedback for adaptive learning"""
        self.record_execution_result(command, tool, success, execution_time)


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Classes
    "EnhancedRouter",
    "AdaptiveRouter",
    "AdaptiveRouteResult",
    # Re-exported from adaptive_router_patterns
    "TaskType",
    "ToolType",
    "RoutePattern",
    "RouteResult",
    "DEFAULT_ROUTE_PATTERNS",
]
