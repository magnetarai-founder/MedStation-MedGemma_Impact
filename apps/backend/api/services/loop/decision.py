"""
Decision Engine

Makes decisions about what to do next based on reflections.
Handles retry logic, plan modifications, and abort conditions.
"""

import logging
from typing import Any

from ..planning import HierarchicalTask, TaskStatus
from .models import (
    Decision,
    DecisionType,
    LoopState,
    Reflection,
    ReflectionAssessment,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Decides what action to take based on reflection.

    Decision types:
    - CONTINUE: Proceed with next planned task
    - RETRY: Retry the failed task
    - MODIFY: Change the plan and continue
    - SKIP: Skip current task, move to next
    - ABORT: Stop execution
    - COMPLETE: Mark as done
    - ASK_USER: Need human input
    """

    # Maximum retries for a single task
    MAX_RETRIES = 3

    # After this many stuck iterations, abort
    STUCK_THRESHOLD = 3

    # Minimum confidence to trust a decision
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(self, llm_client=None):
        """
        Initialize decision engine.

        Args:
            llm_client: Optional LLM for complex decisions
        """
        self.llm_client = llm_client

        # Track retry counts per task
        self.retry_counts: dict[str, int] = {}

        # Track stuck iterations
        self.stuck_count = 0

    async def decide(
        self,
        reflection: Reflection,
        current_task: HierarchicalTask | None,
        loop_state: LoopState,
        next_tasks: list[HierarchicalTask] | None = None,
    ) -> Decision:
        """
        Decide what to do next based on reflection.

        Args:
            reflection: The reflection to base decision on
            current_task: The task that was just executed
            loop_state: Full loop state for context
            next_tasks: Available next tasks

        Returns:
            Decision object
        """
        next_tasks = next_tasks or []

        # Check for completion
        if reflection.assessment == ReflectionAssessment.COMPLETE:
            return self._decide_complete(reflection)

        # Check for stuck pattern
        if reflection.assessment == ReflectionAssessment.STUCK:
            return self._handle_stuck(reflection, current_task, loop_state)

        # Check for error
        if reflection.assessment == ReflectionAssessment.ERROR:
            return self._handle_error(reflection, current_task, loop_state)

        # Check for needed adjustment
        if reflection.assessment == ReflectionAssessment.NEEDS_ADJUSTMENT:
            return self._handle_adjustment(reflection, current_task, next_tasks)

        # On track - continue with next task
        return self._decide_continue(reflection, next_tasks)

    def _decide_complete(self, reflection: Reflection) -> Decision:
        """Handle completion assessment"""
        return Decision(
            reflection_id=reflection.id,
            decision_type=DecisionType.COMPLETE,
            rationale="Reflection indicates goal has been achieved",
        )

    def _decide_continue(
        self, reflection: Reflection, next_tasks: list[HierarchicalTask]
    ) -> Decision:
        """Decide to continue with next task"""
        # Reset stuck counter on progress
        self.stuck_count = 0

        if not next_tasks:
            # No more tasks - we might be done
            if reflection.progress_toward_goal >= 0.9:
                return Decision(
                    reflection_id=reflection.id,
                    decision_type=DecisionType.COMPLETE,
                    rationale="All tasks completed, progress indicates success",
                )
            else:
                return Decision(
                    reflection_id=reflection.id,
                    decision_type=DecisionType.ASK_USER,
                    rationale="No more planned tasks but goal may not be complete",
                    user_question="All planned tasks are complete. Is there anything else needed?",
                )

        # Get next task
        next_task = next_tasks[0]

        return Decision(
            reflection_id=reflection.id,
            decision_type=DecisionType.CONTINUE,
            rationale=f"On track, proceeding with: {next_task.description[:50]}",
            next_action_id=next_task.id,
            next_action_description=next_task.description,
        )

    def _handle_error(
        self,
        reflection: Reflection,
        current_task: HierarchicalTask | None,
        loop_state: LoopState,
    ) -> Decision:
        """Handle error assessment"""
        if current_task is None:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.ABORT,
                rationale="Error occurred but no task context available",
            )

        task_id = current_task.id

        # Check retry count
        current_retries = self.retry_counts.get(task_id, 0)

        if current_retries < self.MAX_RETRIES:
            # Increment retry count
            self.retry_counts[task_id] = current_retries + 1

            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.RETRY,
                rationale=f"Retrying task (attempt {current_retries + 2}/{self.MAX_RETRIES + 1})",
                next_action_id=task_id,
                next_action_description=current_task.description,
            )

        # Max retries exceeded - try to skip or abort
        if self._can_skip_task(current_task, loop_state):
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.SKIP,
                rationale=f"Max retries exceeded, skipping non-critical task",
            )

        return Decision(
            reflection_id=reflection.id,
            decision_type=DecisionType.ABORT,
            rationale=f"Max retries exceeded for critical task: {current_task.description}",
        )

    def _handle_stuck(
        self,
        reflection: Reflection,
        current_task: HierarchicalTask | None,
        loop_state: LoopState,
    ) -> Decision:
        """Handle stuck assessment"""
        self.stuck_count += 1

        if self.stuck_count >= self.STUCK_THRESHOLD:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.ASK_USER,
                rationale="Multiple consecutive stuck states detected",
                user_question=(
                    f"I'm having trouble making progress on: {loop_state.goal}\n"
                    f"Recent issues: {', '.join(reflection.what_went_wrong)}\n"
                    "How would you like me to proceed?"
                ),
            )

        # Try a different approach
        if reflection.suggested_actions:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.MODIFY,
                rationale="Stuck, attempting suggested adjustment",
                modified_plan={"suggested_actions": reflection.suggested_actions},
            )

        return Decision(
            reflection_id=reflection.id,
            decision_type=DecisionType.SKIP,
            rationale="Stuck on task, attempting to skip and continue",
        )

    def _handle_adjustment(
        self,
        reflection: Reflection,
        current_task: HierarchicalTask | None,
        next_tasks: list[HierarchicalTask],
    ) -> Decision:
        """Handle needs_adjustment assessment"""
        # If low confidence, ask user
        if reflection.confidence < self.CONFIDENCE_THRESHOLD:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.ASK_USER,
                rationale="Low confidence in how to adjust",
                user_question=f"I'm uncertain about the next step. {reflection.reasoning}",
            )

        # Try suggested actions
        if reflection.suggested_actions:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.MODIFY,
                rationale=f"Adjusting approach: {reflection.suggested_actions[0]}",
                modified_plan={"suggested_actions": reflection.suggested_actions},
            )

        # Default: continue but note the adjustment need
        if next_tasks:
            return Decision(
                reflection_id=reflection.id,
                decision_type=DecisionType.CONTINUE,
                rationale="Proceeding with caution, may need adjustment",
                next_action_id=next_tasks[0].id,
                next_action_description=next_tasks[0].description,
            )

        return Decision(
            reflection_id=reflection.id,
            decision_type=DecisionType.ASK_USER,
            rationale="Need adjustment but no clear next steps",
            user_question="The current approach may need adjustment. What would you like me to try?",
        )

    def _can_skip_task(
        self, task: HierarchicalTask, loop_state: LoopState
    ) -> bool:
        """Determine if a task can be skipped"""
        from ..planning import TaskPriority

        # Critical tasks cannot be skipped
        if task.priority == TaskPriority.CRITICAL:
            return False

        # Tasks with dependents cannot be skipped easily
        # (Would need to check dependency graph)

        # Optional tasks can be skipped
        if task.priority == TaskPriority.OPTIONAL:
            return True

        # Low priority tasks after some progress can be skipped
        if task.priority == TaskPriority.LOW and loop_state.progress >= 0.5:
            return True

        return False

    def apply_decision(
        self, decision: Decision, task: HierarchicalTask | None
    ) -> None:
        """
        Apply a decision to update task state.

        Args:
            decision: The decision to apply
            task: The task to update
        """
        if task is None:
            return

        if decision.decision_type == DecisionType.COMPLETE:
            task.mark_completed()
        elif decision.decision_type == DecisionType.SKIP:
            task.status = TaskStatus.SKIPPED
        elif decision.decision_type == DecisionType.ABORT:
            task.mark_failed("Aborted by decision engine")

    def reset_retries(self, task_id: str) -> None:
        """Reset retry count for a task"""
        if task_id in self.retry_counts:
            del self.retry_counts[task_id]

    def reset_stuck_count(self) -> None:
        """Reset stuck counter"""
        self.stuck_count = 0

    def get_decision_summary(self, decision: Decision) -> str:
        """Get a human-readable summary of the decision"""
        summaries = {
            DecisionType.CONTINUE: f"Continue with: {decision.next_action_description or 'next task'}",
            DecisionType.RETRY: f"Retry: {decision.next_action_description or 'current task'}",
            DecisionType.MODIFY: f"Modify plan: {decision.rationale}",
            DecisionType.SKIP: "Skip current task and continue",
            DecisionType.ABORT: f"Abort: {decision.rationale}",
            DecisionType.COMPLETE: "Task complete!",
            DecisionType.ASK_USER: f"Asking user: {decision.user_question}",
        }

        return summaries.get(decision.decision_type, str(decision.decision_type))
