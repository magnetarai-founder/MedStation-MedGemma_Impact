"""
Workflow Enums

Static enum definitions for the workflow orchestration system.
Extracted from workflow_models.py during P2 decomposition.

Contains:
- WorkflowTriggerType: How work enters the system
- StageType: Type of work at each stage
- WorkItemStatus: Current state of work items
- WorkItemPriority: Urgency levels
- AssignmentType: How work is assigned
- ConditionOperator: Routing condition operators
- FieldType: Form field types
- WorkflowType: Type of workflow
- NotificationEvent: Events that trigger notifications
"""

from enum import Enum


# ============================================
# WORKFLOW ENUMS
# ============================================

class WorkflowTriggerType(str, Enum):
    """How work enters the system"""
    MANUAL = "manual"              # User creates work item
    FORM_SUBMISSION = "form"       # Form submitted
    SCHEDULE = "schedule"          # Time-based (cron)
    WEBHOOK = "webhook"            # External API call
    EMAIL = "email"                # Email received
    FILE_UPLOAD = "file_upload"    # File dropped
    EVENT = "event"                # System event
    ON_AGENT_EVENT = "on_agent_event"  # Triggered by agent events (Phase D)
    ON_FILE_PATTERN = "on_file_pattern"  # Triggered by file patterns (Phase D)


class StageType(str, Enum):
    """Type of work at this stage"""
    HUMAN = "human"               # Person does work
    AUTOMATION = "automation"     # n8n workflow runs
    HYBRID = "hybrid"             # Person + automation
    AI = "ai"                     # Local AI processing
    APPROVAL = "approval"         # Simple approve/reject
    AGENT_ASSIST = "agent_assist" # AI agent provides suggestions (Phase B)
    CODE_REVIEW = "code_review"   # AI code review with focused prompts (Phase 1)
    TEST_ENRICHMENT = "test_enrichment"  # AI test generation/suggestions (Phase 1)
    DOC_UPDATE = "doc_update"     # AI documentation/release notes (Phase 1)


class WorkItemStatus(str, Enum):
    """Current state of work item"""
    PENDING = "pending"           # Not started
    CLAIMED = "claimed"           # Someone is working on it
    IN_PROGRESS = "in_progress"   # Active work
    WAITING = "waiting"           # Blocked/waiting
    COMPLETED = "completed"       # Done
    CANCELLED = "cancelled"       # Cancelled
    FAILED = "failed"             # Error occurred


class WorkItemPriority(str, Enum):
    """Urgency level"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AssignmentType(str, Enum):
    """How work is assigned"""
    ROLE = "role"                 # Anyone with role can claim
    SPECIFIC_USER = "user"        # Assigned to specific person
    QUEUE = "queue"               # Pull from queue
    AUTOMATION = "automation"     # Auto-assigned
    ROUND_ROBIN = "round_robin"   # Distribute evenly


class ConditionOperator(str, Enum):
    """Routing condition operators"""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class FieldType(str, Enum):
    """Form field types"""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE_UPLOAD = "file_upload"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"


class WorkflowType(str, Enum):
    """Type of workflow"""
    LOCAL_AUTOMATION = "local"  # n8n-style background automation
    TEAM_WORKFLOW = "team"      # Stage-based human task routing


class NotificationEvent(str, Enum):
    """Events that trigger notifications"""
    WORK_ITEM_ASSIGNED = "work_item_assigned"
    WORK_ITEM_CLAIMED = "work_item_claimed"
    WORK_ITEM_COMPLETED = "work_item_completed"
    WORK_ITEM_OVERDUE = "work_item_overdue"
    STAGE_ENTERED = "stage_entered"
    APPROVAL_REQUESTED = "approval_requested"
    COMMENT_ADDED = "comment_added"


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_workflow_statuses() -> list[WorkItemStatus]:
    """Get all possible work item statuses."""
    return list(WorkItemStatus)


def get_active_statuses() -> list[WorkItemStatus]:
    """Get statuses that represent active/in-progress work."""
    return [
        WorkItemStatus.PENDING,
        WorkItemStatus.CLAIMED,
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.WAITING,
    ]


def get_terminal_statuses() -> list[WorkItemStatus]:
    """Get statuses that represent completed work."""
    return [
        WorkItemStatus.COMPLETED,
        WorkItemStatus.CANCELLED,
        WorkItemStatus.FAILED,
    ]


def is_human_stage(stage_type: StageType) -> bool:
    """Check if a stage type requires human interaction."""
    return stage_type in {
        StageType.HUMAN,
        StageType.HYBRID,
        StageType.APPROVAL,
    }


def is_ai_stage(stage_type: StageType) -> bool:
    """Check if a stage type uses AI processing."""
    return stage_type in {
        StageType.AI,
        StageType.AGENT_ASSIST,
        StageType.CODE_REVIEW,
        StageType.TEST_ENRICHMENT,
        StageType.DOC_UPDATE,
    }


__all__ = [
    # Enums
    "WorkflowTriggerType",
    "StageType",
    "WorkItemStatus",
    "WorkItemPriority",
    "AssignmentType",
    "ConditionOperator",
    "FieldType",
    "WorkflowType",
    "NotificationEvent",
    # Helper functions
    "get_all_workflow_statuses",
    "get_active_statuses",
    "get_terminal_statuses",
    "is_human_stage",
    "is_ai_stage",
]
