"""
Workflow Orchestrator Engine - Service Module

State machine for work item lifecycle and stage transitions.

This is the core orchestration engine that was moved from workflow_orchestrator.py
during Phase 6.3e modularization. The top-level workflow_orchestrator.py is now
a backwards compatibility shim.

Responsibilities:
- State machine for work item lifecycle
- Stage transition logic with dependency resolution
- Conditional routing based on data
- SLA tracking and overdue detection
- Queue management and assignment

Extracted from workflow_orchestrator.py during Phase 6.3e modularization.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict

# Import from parent api directory
try:
    from api.workflow_models import (
        WorkItem,
        Workflow,
        Stage,
        StageTransition,
        WorkItemStatus,
        WorkItemPriority,
        StageType,
        AssignmentType,
        ConditionOperator,
        RoutingCondition,
        ConditionalRoute,
    )
    from api.services.workflow_agent_integration import run_agent_assist_for_stage
except ImportError:
    from workflow_models import (
        WorkItem,
        Workflow,
        Stage,
        StageTransition,
        WorkItemStatus,
        WorkItemPriority,
        StageType,
        AssignmentType,
        ConditionOperator,
        RoutingCondition,
        ConditionalRoute,
    )
    from services.workflow_agent_integration import run_agent_assist_for_stage

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Core orchestration engine for workflow execution

    Responsibilities:
    - State machine for work item lifecycle
    - Stage transition logic with dependency resolution
    - Conditional routing based on data
    - SLA tracking and overdue detection
    - Queue management and assignment
    """

    def __init__(self, storage=None):
        self.active_work_items: Dict[str, WorkItem] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.storage = storage  # Optional storage layer

        # Note: Workflows and work items are now loaded per-user on demand
        # No longer loading all data at startup

    def _load_workflows_from_storage(self, user_id: str) -> None:
        """
        Load workflows from storage for a specific user

        Args:
            user_id: User ID for isolation
        """
        if not self.storage:
            return

        workflows = self.storage.list_workflows(user_id=user_id)
        for workflow in workflows:
            self.workflows[workflow.id] = workflow

        logger.info(f"📚 Loaded {len(workflows)} workflows from storage for user {user_id}")

    def _load_active_work_items_from_storage(self, user_id: str) -> None:
        """
        Load active work items from storage for a specific user

        Args:
            user_id: User ID for isolation
        """
        if not self.storage:
            return

        # Load non-completed work items
        try:
            from api.workflow_models import WorkItemStatus as WIS
        except ImportError:
            from workflow_models import WorkItemStatus as WIS
        work_items = self.storage.list_work_items(user_id=user_id, limit=1000)

        active_items = [
            w for w in work_items
            if w.status not in [WorkItemStatus.COMPLETED, WorkItemStatus.CANCELLED]
        ]

        for work_item in active_items:
            self.active_work_items[work_item.id] = work_item

        logger.info(f"📚 Loaded {len(active_items)} active work items from storage for user {user_id}")

    # ============================================
    # WORKFLOW REGISTRATION
    # ============================================

    def register_workflow(self, workflow: Workflow, user_id: str, team_id: Optional[str] = None) -> None:
        """
        Register a workflow definition (Phase 3: team-aware)

        Args:
            workflow: Workflow to register
            user_id: User ID for isolation
            team_id: Optional team ID for team workflows
        """
        self.workflows[workflow.id] = workflow

        # Persist to storage
        if self.storage:
            self.storage.save_workflow(workflow, user_id=user_id, team_id=team_id)

        team_context = f"team={team_id}" if team_id else f"user={user_id}"
        logger.info(f"📋 Registered workflow: {workflow.name} (ID: {workflow.id}) [{team_context}]")
        logger.info(f"   Stages: {len(workflow.stages)}, Triggers: {len(workflow.triggers)}")

    def get_workflow(self, workflow_id: str, user_id: str) -> Optional[Workflow]:
        """
        Get workflow by ID

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation

        Returns:
            Workflow or None if not found
        """
        # Check in-memory cache first
        workflow = self.workflows.get(workflow_id)
        if workflow:
            # Verify ownership through storage if available
            if self.storage:
                stored = self.storage.get_workflow(workflow_id, user_id)
                return stored
            return workflow

        # Fetch from storage
        if self.storage:
            workflow = self.storage.get_workflow(workflow_id, user_id)
            if workflow:
                self.workflows[workflow_id] = workflow
            return workflow

        return None

    def list_workflows(
        self,
        user_id: str,
        category: Optional[str] = None,
        enabled_only: bool = False,
        team_id: Optional[str] = None,
        workflow_type: Optional[str] = None
    ) -> List[Workflow]:
        """
        List all workflows for a user with optional filters (Phase 3: team-aware)

        Args:
            user_id: User ID for isolation
            category: Optional category filter
            enabled_only: Only return enabled workflows
            team_id: Optional team ID for team workflows
            workflow_type: Filter by workflow type ('local' or 'team')

        Returns:
            List of workflows (team or personal based on team_id)
        """
        # Always fetch from storage to ensure user isolation
        if self.storage:
            workflows = self.storage.list_workflows(
                user_id=user_id,
                category=category,
                enabled_only=enabled_only,
                team_id=team_id,
                workflow_type=workflow_type
            )
            return workflows

        # Fallback to in-memory (not recommended for multi-user)
        workflows = list(self.workflows.values())

        # Apply filters
        if category:
            workflows = [w for w in workflows if w.category == category]
        if enabled_only:
            workflows = [w for w in workflows if w.enabled]
        if workflow_type:
            try:
                from api.workflow_models import WorkflowType
            except ImportError:
                from workflow_models import WorkflowType
            workflow_type_enum = WorkflowType.LOCAL_AUTOMATION if workflow_type == 'local' else WorkflowType.TEAM_WORKFLOW
            workflows = [w for w in workflows if w.workflow_type == workflow_type_enum]

        return workflows

    # ============================================
    # WORK ITEM CREATION
    # ============================================

    def create_work_item(
        self,
        workflow_id: str,
        user_id: str,
        data: Dict[str, Any],
        created_by: str,
        priority: WorkItemPriority = WorkItemPriority.NORMAL,
        tags: Optional[List[str]] = None
    ) -> WorkItem:
        """
        Create new work item and place in first stage

        Args:
            workflow_id: Workflow template to use
            user_id: User ID for isolation
            data: Initial data payload
            created_by: User ID who created this
            priority: Priority level
            tags: Optional tags for filtering

        Returns:
            Created work item

        Raises:
            ValueError: If workflow not found or has no stages
        """
        workflow = self.get_workflow(workflow_id, user_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if not workflow.stages:
            raise ValueError(f"Workflow has no stages: {workflow.name}")

        # Find first stage (lowest order)
        first_stage = min(workflow.stages, key=lambda s: s.order)

        # Create work item
        work_item = WorkItem(
            workflow_id=workflow_id,
            workflow_name=workflow.name,
            current_stage_id=first_stage.id,
            current_stage_name=first_stage.name,
            status=WorkItemStatus.PENDING,
            priority=priority,
            data=data,
            created_by=created_by,
            tags=tags or [],
        )

        # Calculate SLA if stage has time limit
        if first_stage.sla_minutes:
            work_item.sla_due_at = datetime.now(UTC) + timedelta(minutes=first_stage.sla_minutes)

        # Record initial transition
        transition = StageTransition(
            from_stage_id=None,  # No previous stage
            to_stage_id=first_stage.id,
            transitioned_by=created_by,
            notes="Work item created"
        )
        work_item.history.append(transition)

        # Auto-assign if stage requires it
        self._auto_assign_if_needed(work_item, first_stage)

        # Store active work item
        self.active_work_items[work_item.id] = work_item

        # Persist to storage
        if self.storage:
            self.storage.save_work_item(work_item, user_id=user_id)

        logger.info(f"✨ Created work item: {work_item.id} for user {user_id}")
        logger.info(f"   Workflow: {workflow.name}")
        logger.info(f"   Initial Stage: {first_stage.name}")
        logger.info(f"   Priority: {priority.value}")

        return work_item

    def list_work_items(
        self,
        user_id: str,
        workflow_id: Optional[str] = None,
        status: Optional[WorkItemStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[WorkItemPriority] = None,
        limit: int = 50
    ) -> List[WorkItem]:
        """
        List work items for a user with optional filters

        Args:
            user_id: User ID for isolation
            workflow_id: Optional workflow filter
            status: Optional status filter
            assigned_to: Optional assignment filter
            priority: Optional priority filter
            limit: Maximum number of items to return

        Returns:
            List of work items owned by user
        """
        # Always fetch from storage to ensure user isolation
        if self.storage:
            items = self.storage.list_work_items(
                user_id=user_id,
                workflow_id=workflow_id,
                status=status,
                limit=limit
            )

            # Apply additional filters not supported by storage
            if assigned_to:
                items = [w for w in items if w.assigned_to == assigned_to]
            if priority:
                items = [w for w in items if w.priority == priority]

            return items[:limit]

        # Fallback to in-memory (not recommended for multi-user)
        items = list(self.active_work_items.values())

        # Apply filters
        if workflow_id:
            items = [w for w in items if w.workflow_id == workflow_id]
        if status:
            items = [w for w in items if w.status == status]
        if assigned_to:
            items = [w for w in items if w.assigned_to == assigned_to]
        if priority:
            items = [w for w in items if w.priority == priority]

        # Sort by created_at desc
        items.sort(key=lambda w: w.created_at, reverse=True)

        return items[:limit]

    # ============================================
    # WORK ITEM CLAIMING
    # ============================================

    def claim_work_item(self, work_item_id: str, user_id: str) -> WorkItem:
        """
        User claims a work item from queue

        Args:
            work_item_id: ID of work item to claim
            user_id: User claiming the item (also used for ownership check)

        Returns:
            Updated work item

        Raises:
            ValueError: If work item not found, not owned by user, or already claimed
        """
        # Try in-memory first
        work_item = self.active_work_items.get(work_item_id)

        # Verify ownership via storage
        if self.storage:
            work_item = self.storage.get_work_item(work_item_id, user_id)
            if not work_item:
                raise ValueError(f"Work item not found or not accessible: {work_item_id}")
        elif not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")

        if work_item.status not in [WorkItemStatus.PENDING]:
            raise ValueError(f"Work item cannot be claimed (status: {work_item.status.value})")

        # Claim the item
        work_item.assigned_to = user_id
        work_item.claimed_at = datetime.now(UTC)
        work_item.status = WorkItemStatus.CLAIMED
        work_item.updated_at = datetime.now(UTC)

        # Update in-memory cache
        self.active_work_items[work_item_id] = work_item

        # Persist to storage
        if self.storage:
            self.storage.save_work_item(work_item, user_id=user_id)

        logger.info(f"👤 Work item claimed: {work_item_id} by user {user_id}")

        return work_item

    def start_work(self, work_item_id: str, user_id: str) -> WorkItem:
        """
        Mark work item as in progress

        Args:
            work_item_id: ID of work item
            user_id: User starting work (also used for ownership check)

        Returns:
            Updated work item

        Raises:
            ValueError: If work item not found, not owned by user, or not assigned to user
        """
        # Try in-memory first
        work_item = self.active_work_items.get(work_item_id)

        # Verify ownership via storage
        if self.storage:
            work_item = self.storage.get_work_item(work_item_id, user_id)
            if not work_item:
                raise ValueError(f"Work item not found or not accessible: {work_item_id}")
        elif not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")

        if work_item.assigned_to != user_id:
            raise ValueError(f"Work item not assigned to user {user_id}")

        work_item.status = WorkItemStatus.IN_PROGRESS
        work_item.updated_at = datetime.now(UTC)

        # Update in-memory cache
        self.active_work_items[work_item_id] = work_item

        # Persist to storage
        if self.storage:
            self.storage.save_work_item(work_item, user_id=user_id)

        logger.info(f"▶️  Work started: {work_item_id} by user {user_id}")

        return work_item

    # ============================================
    # STAGE COMPLETION & TRANSITION
    # ============================================

    def complete_stage(
        self,
        work_item_id: str,
        user_id: str,
        stage_data: Dict[str, Any],
        notes: Optional[str] = None
    ) -> WorkItem:
        """
        Complete current stage and transition to next stage

        Args:
            work_item_id: ID of work item
            user_id: User completing the stage (also used for ownership check)
            stage_data: Data collected at this stage
            notes: Optional notes about completion

        Returns:
            Updated work item (possibly in new stage)

        Raises:
            ValueError: If work item not found, not owned by user, or invalid state
        """
        # Try in-memory first
        work_item = self.active_work_items.get(work_item_id)

        # Verify ownership via storage
        if self.storage:
            work_item = self.storage.get_work_item(work_item_id, user_id)
            if not work_item:
                raise ValueError(f"Work item not found or not accessible: {work_item_id}")
        elif not work_item:
            raise ValueError(f"Work item not found: {work_item_id}")

        workflow = self.get_workflow(work_item.workflow_id, user_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {work_item.workflow_id}")

        # Find current stage
        current_stage = self._find_stage(workflow, work_item.current_stage_id)
        if not current_stage:
            raise ValueError(f"Current stage not found: {work_item.current_stage_id}")

        # Merge stage data into work item data
        work_item.data.update(stage_data)
        work_item.updated_at = datetime.now(UTC)

        # Calculate time spent in this stage
        last_transition = work_item.history[-1] if work_item.history else None
        duration_seconds = None
        if last_transition:
            duration = datetime.now(UTC) - last_transition.transitioned_at
            duration_seconds = int(duration.total_seconds())

        logger.info(f"✅ Stage completed: {current_stage.name} for work item {work_item_id}")
        logger.info(f"   Duration: {duration_seconds}s" if duration_seconds else "   Duration: N/A")

        # Determine next stage using conditional routing
        next_stage = self._determine_next_stage(current_stage, work_item, user_id)

        if next_stage:
            # Transition to next stage
            self._transition_to_stage(
                work_item,
                workflow,
                next_stage,
                user_id,
                notes,
                duration_seconds
            )
        else:
            # No next stage - workflow complete
            work_item.status = WorkItemStatus.COMPLETED
            work_item.completed_at = datetime.now(UTC)

            transition = StageTransition(
                from_stage_id=current_stage.id,
                to_stage_id=None,  # No next stage
                transitioned_by=user_id,
                notes=notes or "Workflow completed",
                duration_seconds=duration_seconds
            )
            work_item.history.append(transition)

            logger.info(f"🎉 Workflow completed: {work_item_id}")

        # Update in-memory cache
        self.active_work_items[work_item_id] = work_item

        # Persist to storage
        if self.storage:
            self.storage.save_work_item(work_item, user_id=user_id)

        return work_item

    # ============================================
    # CONDITIONAL ROUTING
    # ============================================

    def _determine_next_stage(
        self,
        current_stage: Stage,
        work_item: WorkItem,
        user_id: str
    ) -> Optional[Stage]:
        """
        Determine next stage based on conditional routing

        Args:
            current_stage: Current stage definition
            work_item: Work item with data
            user_id: User ID for isolation

        Returns:
            Next stage, or None if workflow complete
        """
        if not current_stage.next_stages:
            return None

        # Find first matching route
        for route in current_stage.next_stages:
            if not route.conditions:
                # Default route (no conditions)
                workflow = self.get_workflow(work_item.workflow_id, user_id)
                if workflow:
                    return self._find_stage(workflow, route.next_stage_id)
            else:
                # Check all conditions
                if self._evaluate_conditions(route.conditions, work_item.data):
                    workflow = self.get_workflow(work_item.workflow_id, user_id)
                    if workflow:
                        logger.info(f"🔀 Conditional route matched: {route.description or route.next_stage_id}")
                        return self._find_stage(workflow, route.next_stage_id)

        # No matching route
        logger.warning(f"⚠️  No matching route found for work item {work_item.id}")
        return None

    def _evaluate_conditions(
        self,
        conditions: List[RoutingCondition],
        data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate all conditions (AND logic)

        Args:
            conditions: List of conditions to check
            data: Work item data

        Returns:
            True if all conditions match
        """
        for condition in conditions:
            field_value = data.get(condition.field)
            target_value = condition.value

            # Evaluate based on operator
            if condition.operator == ConditionOperator.EQUALS:
                if field_value != target_value:
                    return False
            elif condition.operator == ConditionOperator.NOT_EQUALS:
                if field_value == target_value:
                    return False
            elif condition.operator == ConditionOperator.GREATER_THAN:
                if not (field_value and field_value > target_value):
                    return False
            elif condition.operator == ConditionOperator.LESS_THAN:
                if not (field_value and field_value < target_value):
                    return False
            elif condition.operator == ConditionOperator.CONTAINS:
                if not (field_value and target_value in str(field_value)):
                    return False
            elif condition.operator == ConditionOperator.NOT_CONTAINS:
                if field_value and target_value in str(field_value):
                    return False
            elif condition.operator == ConditionOperator.IS_TRUE:
                if not field_value:
                    return False
            elif condition.operator == ConditionOperator.IS_FALSE:
                if field_value:
                    return False

        return True

    # ============================================
    # STAGE TRANSITIONS
    # ============================================

    def _transition_to_stage(
        self,
        work_item: WorkItem,
        workflow: Workflow,
        next_stage: Stage,
        user_id: str,
        notes: Optional[str],
        duration_seconds: Optional[int]
    ) -> None:
        """
        Transition work item to new stage

        Args:
            work_item: Work item to transition
            workflow: Workflow definition
            next_stage: Target stage
            user_id: User performing transition
            notes: Optional transition notes
            duration_seconds: Time spent in previous stage
        """
        old_stage_id = work_item.current_stage_id

        # Update work item
        work_item.current_stage_id = next_stage.id
        work_item.current_stage_name = next_stage.name
        work_item.status = WorkItemStatus.PENDING  # Reset to pending for new stage
        work_item.assigned_to = None  # Unassign for new stage
        work_item.claimed_at = None

        # Calculate new SLA if stage has time limit
        if next_stage.sla_minutes:
            work_item.sla_due_at = datetime.now(UTC) + timedelta(minutes=next_stage.sla_minutes)
        else:
            work_item.sla_due_at = None
            work_item.is_overdue = False

        # Record transition
        transition = StageTransition(
            from_stage_id=old_stage_id,
            to_stage_id=next_stage.id,
            transitioned_by=user_id,
            notes=notes or f"Transitioned to {next_stage.name}",
            duration_seconds=duration_seconds
        )
        work_item.history.append(transition)

        # Auto-assign if needed
        self._auto_assign_if_needed(work_item, next_stage)

        logger.info(f"→ Transitioned to stage: {next_stage.name}")

        # Auto-execute if automation stage
        if next_stage.stage_type == StageType.AUTOMATION and next_stage.automation:
            logger.info(f"🤖 Auto-executing automation stage: {next_stage.name}")
            # TODO: Trigger automation (n8n, local AI, etc.)

        # Agent Assist stage hook (Phase B - non-destructive, advisory only)
        if next_stage.stage_type == StageType.AGENT_ASSIST:
            logger.info(f"🤖 Agent Assist triggered for stage: {next_stage.name}")
            if self.storage:
                try:
                    # Run agent assist synchronously in Phase B
                    # Phase C+ can make this async/background if needed
                    run_agent_assist_for_stage(
                        storage=self.storage,
                        work_item=work_item,
                        stage=next_stage,
                        user_id=user_id,
                    )
                except Exception as e:
                    # Agent assist errors are already logged and stored in work_item.data
                    # Don't let them break the transition
                    logger.warning(f"Agent Assist encountered error (graceful degradation): {e}")

    # ============================================
    # ASSIGNMENT LOGIC
    # ============================================

    def _auto_assign_if_needed(self, work_item: WorkItem, stage: Stage) -> None:
        """
        Auto-assign work item if stage requires it

        Args:
            work_item: Work item to assign
            stage: Stage definition
        """
        if stage.assignment_type == AssignmentType.SPECIFIC_USER:
            if stage.assigned_user_id:
                work_item.assigned_to = stage.assigned_user_id
                work_item.status = WorkItemStatus.CLAIMED
                work_item.claimed_at = datetime.now(UTC)
                logger.info(f"👤 Auto-assigned to user: {stage.assigned_user_id}")

        elif stage.assignment_type == AssignmentType.AUTOMATION:
            work_item.assigned_to = "system"
            work_item.status = WorkItemStatus.IN_PROGRESS
            logger.info(f"🤖 Auto-assigned to automation")

    # ============================================
    # QUEUE MANAGEMENT
    # ============================================

    def get_queue_for_role(
        self,
        workflow_id: str,
        role_name: str,
        user_id: str,
        stage_id: Optional[str] = None
    ) -> List[WorkItem]:
        """
        Get all work items in queue for a role

        Args:
            workflow_id: Filter by workflow
            role_name: Role name to filter by
            user_id: User ID for isolation
            stage_id: Optional stage filter

        Returns:
            List of work items available for this role (filtered by user)
        """
        queue = []

        workflow = self.get_workflow(workflow_id, user_id)
        if not workflow:
            return queue

        # Load work items for this user from storage if available
        if self.storage:
            work_items = self.storage.list_work_items(
                user_id=user_id,
                workflow_id=workflow_id,
                status=WorkItemStatus.PENDING,
                limit=1000
            )
        else:
            # Use in-memory cache (already filtered by user during load)
            work_items = [w for w in self.active_work_items.values() if w.workflow_id == workflow_id]

        for work_item in work_items:
            # Filter by stage if specified
            if stage_id and work_item.current_stage_id != stage_id:
                continue

            # Only pending items
            if work_item.status != WorkItemStatus.PENDING:
                continue

            # Check if current stage matches role
            stage = self._find_stage(workflow, work_item.current_stage_id)
            if stage and stage.role_name == role_name:
                queue.append(work_item)

        # Sort by priority, then age
        queue.sort(key=lambda w: (
            -self._priority_score(w.priority),
            w.created_at
        ))

        return queue

    def get_my_active_work(self, user_id: str) -> List[WorkItem]:
        """
        Get all work items assigned to or claimed by user

        Args:
            user_id: User ID (also used for ownership filter)

        Returns:
            List of work items for this user (filtered by ownership)
        """
        my_work = []

        # Load work items for this user from storage if available
        if self.storage:
            # Fetch all active work items for this user
            claimed_items = self.storage.list_work_items(
                user_id=user_id,
                status=WorkItemStatus.CLAIMED,
                limit=1000
            )
            in_progress_items = self.storage.list_work_items(
                user_id=user_id,
                status=WorkItemStatus.IN_PROGRESS,
                limit=1000
            )
            my_work = claimed_items + in_progress_items

            # Filter by assigned_to
            my_work = [w for w in my_work if w.assigned_to == user_id]
        else:
            # Use in-memory cache (already filtered by user during load)
            for work_item in self.active_work_items.values():
                if work_item.assigned_to == user_id:
                    if work_item.status in [WorkItemStatus.CLAIMED, WorkItemStatus.IN_PROGRESS]:
                        my_work.append(work_item)

        # Sort by priority, then SLA
        my_work.sort(key=lambda w: (
            -self._priority_score(w.priority),
            w.sla_due_at or datetime.max
        ))

        return my_work

    # ============================================
    # SLA TRACKING
    # ============================================

    def check_overdue_items(self, user_id: str) -> List[WorkItem]:
        """
        Check active work items for SLA violations

        Args:
            user_id: User ID for isolation

        Returns:
            List of overdue work items (filtered by user)
        """
        now = datetime.now(UTC)
        overdue = []

        # Load work items for this user from storage if available
        if self.storage:
            work_items = self.storage.list_work_items(user_id=user_id, limit=1000)
        else:
            # Use in-memory cache (already filtered by user during load)
            work_items = self.active_work_items.values()

        for work_item in work_items:
            if work_item.status == WorkItemStatus.COMPLETED:
                continue

            if work_item.sla_due_at and now > work_item.sla_due_at:
                if not work_item.is_overdue:
                    work_item.is_overdue = True
                    # Update in-memory cache
                    self.active_work_items[work_item.id] = work_item
                    # Persist to storage
                    if self.storage:
                        self.storage.save_work_item(work_item, user_id=user_id)
                    logger.warning(f"⏰ Work item overdue: {work_item.id} ({work_item.workflow_name}) for user {user_id}")
                overdue.append(work_item)

        return overdue

    # ============================================
    # UTILITIES
    # ============================================

    def _find_stage(self, workflow: Workflow, stage_id: str) -> Optional[Stage]:
        """Find stage by ID in workflow"""
        for stage in workflow.stages:
            if stage.id == stage_id:
                return stage
        return None

    def _priority_score(self, priority: WorkItemPriority) -> int:
        """Convert priority to numeric score for sorting"""
        scores = {
            WorkItemPriority.LOW: 1,
            WorkItemPriority.NORMAL: 2,
            WorkItemPriority.HIGH: 3,
            WorkItemPriority.URGENT: 4,
        }
        return scores.get(priority, 2)

    # ============================================
    # STATISTICS
    # ============================================

    def get_workflow_statistics(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for a workflow

        Args:
            workflow_id: Workflow ID
            user_id: User ID for isolation

        Returns:
            Dictionary of statistics (filtered by user)
        """
        # Load work items for this user from storage if available
        if self.storage:
            items = self.storage.list_work_items(
                user_id=user_id,
                workflow_id=workflow_id,
                limit=10000
            )
        else:
            # Use in-memory cache (already filtered by user during load)
            items = [w for w in self.active_work_items.values() if w.workflow_id == workflow_id]

        total = len(items)
        completed = len([w for w in items if w.status == WorkItemStatus.COMPLETED])
        active = len([w for w in items if w.status in [WorkItemStatus.CLAIMED, WorkItemStatus.IN_PROGRESS]])
        pending = len([w for w in items if w.status == WorkItemStatus.PENDING])
        overdue = len([w for w in items if w.is_overdue])

        return {
            "total_items": total,
            "completed": completed,
            "active": active,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
        }
