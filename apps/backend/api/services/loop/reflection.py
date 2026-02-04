"""
Reflection Engine

Analyzes observations to understand what happened and why.
Uses LLM for intelligent reflection with heuristic fallbacks.
"""

import json
import logging
from typing import Any

from .models import (
    LoopState,
    Observation,
    Reflection,
    ReflectionAssessment,
)

logger = logging.getLogger(__name__)


# Reflection prompt template
REFLECTION_PROMPT = """You are an AI agent reflecting on your recent action.

Goal: {goal}

Action Taken:
- Description: {action_description}
- Success: {success}
- Output: {output}
- Error: {error}

Files Modified: {files_modified}
Duration: {duration_ms}ms

Previous Actions Summary:
{history}

Analyze this outcome:
1. Did this action move us closer to the goal?
2. What went well?
3. What went wrong (if anything)?
4. What should we do next?
5. What can we learn from this?

Respond ONLY with valid JSON:
{{
  "assessment": "on_track|needs_adjustment|stuck|error|complete",
  "confidence": 0.0-1.0,
  "reasoning": "Why this assessment",
  "what_went_well": ["..."],
  "what_went_wrong": ["..."],
  "suggested_actions": ["..."],
  "lessons_learned": ["..."],
  "progress_toward_goal": 0.0-1.0,
  "estimated_remaining_steps": N
}}"""


class ReflectionEngine:
    """
    Analyzes observations to produce reflections.

    The reflection helps the agent understand:
    - Whether it's making progress
    - What adjustments might be needed
    - What to try next
    """

    def __init__(self, llm_client=None):
        """
        Initialize reflection engine.

        Args:
            llm_client: LLM client for intelligent reflection
        """
        self.llm_client = llm_client

    async def reflect(
        self,
        observation: Observation,
        goal: str,
        history: list[Observation] | None = None,
        loop_state: LoopState | None = None,
    ) -> Reflection:
        """
        Generate reflection on an observation.

        Args:
            observation: The observation to reflect on
            goal: The overall goal we're trying to achieve
            history: Previous observations for context
            loop_state: Full loop state for additional context

        Returns:
            Reflection object
        """
        if self.llm_client:
            return await self._reflect_with_llm(observation, goal, history, loop_state)
        else:
            return self._reflect_with_heuristics(observation, goal, history)

    async def _reflect_with_llm(
        self,
        observation: Observation,
        goal: str,
        history: list[Observation] | None,
        loop_state: LoopState | None,
    ) -> Reflection:
        """Use LLM for intelligent reflection"""
        # Format history
        history_str = self._format_history(history or [])

        # Format output (truncate if needed)
        output_str = str(observation.output)[:500] if observation.output else "None"

        prompt = REFLECTION_PROMPT.format(
            goal=goal,
            action_description=observation.action_description,
            success=observation.success,
            output=output_str,
            error=observation.error or "None",
            files_modified=", ".join(observation.files_modified) or "None",
            duration_ms=observation.duration_ms,
            history=history_str,
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                format="json",
            )

            content = response.get("message", {}).get("content", "{}")
            result = json.loads(content)

            return self._parse_reflection(result, observation.id)

        except Exception as e:
            logger.warning(f"LLM reflection failed: {e}, using heuristics")
            return self._reflect_with_heuristics(observation, goal, history)

    def _reflect_with_heuristics(
        self,
        observation: Observation,
        goal: str,
        history: list[Observation] | None,
    ) -> Reflection:
        """Generate reflection using heuristics"""
        history = history or []

        # Determine assessment based on success and patterns
        assessment = self._assess_observation(observation, history)
        confidence = self._calculate_confidence(observation, history)

        # Analyze what went well/wrong
        what_went_well = []
        what_went_wrong = []

        if observation.success:
            what_went_well.append("Action completed successfully")
            if observation.files_modified:
                what_went_well.append(f"Modified {len(observation.files_modified)} files")
            if observation.duration_ms < 5000:
                what_went_well.append("Completed quickly")
        else:
            what_went_wrong.append(f"Action failed: {observation.error}")

        # Suggest next actions
        suggested_actions = self._suggest_actions(observation, assessment)

        # Extract lessons
        lessons_learned = self._extract_lessons(observation, history)

        # Estimate progress
        progress = self._estimate_progress(observation, history, goal)
        remaining = self._estimate_remaining_steps(observation, history, goal)

        return Reflection(
            observation_id=observation.id,
            assessment=assessment,
            confidence=confidence,
            reasoning=self._generate_reasoning(observation, assessment),
            what_went_well=what_went_well,
            what_went_wrong=what_went_wrong,
            suggested_actions=suggested_actions,
            lessons_learned=lessons_learned,
            progress_toward_goal=progress,
            estimated_remaining_steps=remaining,
        )

    def _assess_observation(
        self, observation: Observation, history: list[Observation]
    ) -> ReflectionAssessment:
        """Determine assessment from observation"""
        # Success case
        if observation.success:
            # Check if we might be done
            if self._looks_complete(observation):
                return ReflectionAssessment.COMPLETE
            return ReflectionAssessment.ON_TRACK

        # Error case - check for patterns
        recent_failures = sum(1 for o in history[-3:] if not o.success)

        if recent_failures >= 3:
            return ReflectionAssessment.STUCK

        # Check if error is similar to previous
        if self._is_repeated_error(observation, history):
            return ReflectionAssessment.STUCK

        return ReflectionAssessment.ERROR

    def _looks_complete(self, observation: Observation) -> bool:
        """Check if observation suggests completion"""
        if not observation.output:
            return False

        output_str = str(observation.output).lower()
        completion_indicators = [
            "all tests passed",
            "success",
            "completed successfully",
            "no errors",
            "build succeeded",
        ]

        return any(indicator in output_str for indicator in completion_indicators)

    def _is_repeated_error(
        self, observation: Observation, history: list[Observation]
    ) -> bool:
        """Check if this is the same error as before"""
        if not observation.error:
            return False

        current_error = observation.error.lower()

        for past_obs in history[-3:]:
            if past_obs.error and past_obs.error.lower() == current_error:
                return True

        return False

    def _calculate_confidence(
        self, observation: Observation, history: list[Observation]
    ) -> float:
        """Calculate confidence in the assessment"""
        base_confidence = 0.7

        # Higher confidence for clear success/failure
        if observation.success and observation.files_modified:
            base_confidence += 0.1

        if observation.error and len(observation.error) > 10:
            base_confidence += 0.1  # Clear error message

        # Lower confidence if inconsistent with history
        if history:
            recent_success_rate = sum(1 for o in history[-3:] if o.success) / min(
                3, len(history)
            )
            if observation.success and recent_success_rate < 0.5:
                base_confidence -= 0.1  # Unexpected success
            elif not observation.success and recent_success_rate > 0.8:
                base_confidence -= 0.1  # Unexpected failure

        return min(max(base_confidence, 0.3), 1.0)

    def _suggest_actions(
        self, observation: Observation, assessment: ReflectionAssessment
    ) -> list[str]:
        """Suggest next actions based on assessment"""
        if assessment == ReflectionAssessment.COMPLETE:
            return ["Verify final result", "Clean up temporary files"]

        if assessment == ReflectionAssessment.ON_TRACK:
            return ["Continue with next planned step"]

        if assessment == ReflectionAssessment.ERROR:
            suggestions = ["Analyze the error message"]
            if observation.error:
                if "not found" in observation.error.lower():
                    suggestions.append("Check if the file/resource exists")
                if "permission" in observation.error.lower():
                    suggestions.append("Check file permissions")
                if "syntax" in observation.error.lower():
                    suggestions.append("Review code for syntax errors")
            suggestions.append("Try a different approach")
            return suggestions

        if assessment == ReflectionAssessment.STUCK:
            return [
                "Step back and reconsider the approach",
                "Try a completely different strategy",
                "Consider asking for help",
            ]

        return ["Proceed carefully"]

    def _extract_lessons(
        self, observation: Observation, history: list[Observation]
    ) -> list[str]:
        """Extract lessons learned from observation"""
        lessons = []

        if observation.success and observation.duration_ms > 10000:
            lessons.append("This type of operation takes significant time")

        if not observation.success and observation.error:
            error_lower = observation.error.lower()
            if "timeout" in error_lower:
                lessons.append("Consider increasing timeout for long operations")
            if "memory" in error_lower:
                lessons.append("Watch for memory constraints")

        # Learn from recovery
        if observation.success and history:
            last_obs = history[-1] if history else None
            if last_obs and not last_obs.success:
                lessons.append("Successfully recovered from previous failure")

        return lessons

    def _estimate_progress(
        self, observation: Observation, history: list[Observation], goal: str
    ) -> float:
        """Estimate progress toward goal"""
        if not history:
            return 0.1 if observation.success else 0.0

        total = len(history) + 1
        successes = sum(1 for o in history if o.success) + (1 if observation.success else 0)

        # Base progress on success rate
        base_progress = successes / max(total, 1) * 0.8

        # Boost if files were modified
        if observation.files_modified:
            base_progress += 0.1

        return min(base_progress, 1.0)

    def _estimate_remaining_steps(
        self, observation: Observation, history: list[Observation], goal: str
    ) -> int:
        """Estimate remaining steps to complete goal"""
        # Simple heuristic based on history
        completed = len(history) + 1
        failures = sum(1 for o in history if not o.success)

        # Assume roughly 10 steps for a typical task
        base_estimate = 10
        remaining = max(base_estimate - completed + failures, 1)

        if self._looks_complete(observation):
            remaining = 0

        return remaining

    def _generate_reasoning(
        self, observation: Observation, assessment: ReflectionAssessment
    ) -> str:
        """Generate reasoning string for the assessment"""
        if assessment == ReflectionAssessment.COMPLETE:
            return "The action succeeded and indicators suggest the goal is achieved."

        if assessment == ReflectionAssessment.ON_TRACK:
            if observation.files_modified:
                return f"Action succeeded, modified {len(observation.files_modified)} files."
            return "Action completed successfully."

        if assessment == ReflectionAssessment.ERROR:
            return f"Action failed with error: {observation.error or 'Unknown'}"

        if assessment == ReflectionAssessment.STUCK:
            return "Multiple consecutive failures detected, may need different approach."

        return "Assessment based on action outcome."

    def _format_history(self, history: list[Observation]) -> str:
        """Format observation history for prompt"""
        if not history:
            return "No previous actions"

        lines = []
        for obs in history[-5:]:  # Last 5 observations
            status = "✓" if obs.success else "✗"
            lines.append(f"- {status} {obs.action_description[:50]}")

        return "\n".join(lines)

    def _parse_reflection(self, result: dict[str, Any], observation_id: str) -> Reflection:
        """Parse LLM response into Reflection object"""
        assessment_map = {
            "on_track": ReflectionAssessment.ON_TRACK,
            "needs_adjustment": ReflectionAssessment.NEEDS_ADJUSTMENT,
            "stuck": ReflectionAssessment.STUCK,
            "error": ReflectionAssessment.ERROR,
            "complete": ReflectionAssessment.COMPLETE,
        }

        return Reflection(
            observation_id=observation_id,
            assessment=assessment_map.get(
                result.get("assessment", ""), ReflectionAssessment.ON_TRACK
            ),
            confidence=float(result.get("confidence", 0.7)),
            reasoning=result.get("reasoning", ""),
            what_went_well=result.get("what_went_well", []),
            what_went_wrong=result.get("what_went_wrong", []),
            suggested_actions=result.get("suggested_actions", []),
            lessons_learned=result.get("lessons_learned", []),
            progress_toward_goal=float(result.get("progress_toward_goal", 0.0)),
            estimated_remaining_steps=int(result.get("estimated_remaining_steps", 5)),
        )
