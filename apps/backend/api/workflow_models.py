"""
Universal Workflow Data Models
Industry-agnostic abstractions for distributed work orchestration
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# ENUMS
# ============================================

class WorkflowTriggerType(str, Enum):
    """How work enters the system"""
    MANUAL = "manual"              # User creates work item
    FORM_SUBMISSION = "form"       # Form submitted
    SCHEDULE = "schedule"          # Time-based (cron)
    WEBHOOK = "webhook"            # External API call
    EMAIL = "email"                # Email received
    FILE_UPLOAD = "file_upload"   # File dropped
    EVENT = "event"                # System event


class StageType(str, Enum):
    """Type of work at this stage"""
    HUMAN = "human"               # Person does work
    AUTOMATION = "automation"     # n8n workflow runs
    HYBRID = "hybrid"             # Person + automation
    AI = "ai"                     # Local AI processing
    APPROVAL = "approval"         # Simple approve/reject


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


# ============================================
# FORM DEFINITIONS
# ============================================

class FormFieldOption(BaseModel):
    """Option for select/radio fields"""
    value: str
    label: str


class FormField(BaseModel):
    """Field definition for data collection"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # Internal field name
    label: str                         # Display label
    type: FieldType
    required: bool = False
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None

    # Validation
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None      # Regex pattern

    # Options for select/radio/checkbox
    options: Optional[List[FormFieldOption]] = None

    # Conditional display
    show_if: Optional[Dict[str, Any]] = None


class FormDefinition(BaseModel):
    """Form for data collection at a stage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    fields: List[FormField]
    submit_button_text: str = "Submit"


# ============================================
# ROUTING & CONDITIONS
# ============================================

class RoutingCondition(BaseModel):
    """Condition for conditional routing"""
    field: str                         # Field name to check
    operator: ConditionOperator
    value: Any                         # Value to compare against


class ConditionalRoute(BaseModel):
    """Next stage based on conditions"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    next_stage_id: str
    conditions: Optional[List[RoutingCondition]] = None  # If None, default route
    notify: bool = True                # Send notification
    description: Optional[str] = None  # Human-readable condition


# ============================================
# AUTOMATION CONFIG
# ============================================

class AutomationConfig(BaseModel):
    """Configuration for automation stage"""
    type: Literal["n8n", "local_ai", "custom"]

    # For n8n workflows
    n8n_workflow_id: Optional[str] = None
    n8n_webhook_url: Optional[str] = None

    # For local AI
    ai_model: Optional[str] = None     # "llama3", "qwen", etc.
    ai_prompt_template: Optional[str] = None

    # For custom automations
    custom_script_path: Optional[str] = None

    # Parameters to pass
    parameters: Optional[Dict[str, Any]] = None

    # Timeout
    timeout_seconds: int = 300


# ============================================
# WORKFLOW STAGES
# ============================================

class Stage(BaseModel):
    """A stage in a workflow"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # "Triage", "Attorney Review"
    description: Optional[str] = None
    stage_type: StageType

    # Assignment
    assignment_type: AssignmentType
    role_name: Optional[str] = None    # For role-based assignment
    assigned_user_id: Optional[str] = None  # For specific user

    # Data collection
    form: Optional[FormDefinition] = None

    # Automation
    automation: Optional[AutomationConfig] = None

    # Business rules
    sla_minutes: Optional[int] = None  # Time limit
    requires_approval: bool = False
    auto_advance: bool = False         # Auto-move to next on completion

    # Routing
    next_stages: List[ConditionalRoute] = []

    # Notifications
    notify_on_arrival: bool = True
    notify_on_overdue: bool = True

    # AI assistance
    ai_suggestions_enabled: bool = False
    ai_suggestion_prompt: Optional[str] = None

    # Metadata
    order: int = 0                     # Display order
    color: Optional[str] = None        # For UI visualization


# ============================================
# WORKFLOW DEFINITION
# ============================================

class WorkflowTrigger(BaseModel):
    """How work enters this workflow"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_type: WorkflowTriggerType

    # For form triggers
    form_id: Optional[str] = None

    # For schedule triggers
    cron_expression: Optional[str] = None

    # For webhook triggers
    webhook_url: Optional[str] = None

    # For email triggers
    email_address: Optional[str] = None
    email_filter: Optional[Dict[str, Any]] = None

    enabled: bool = True


class Workflow(BaseModel):
    """Complete workflow definition"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # "Patient Care", "Legal Case Management"
    description: Optional[str] = None
    icon: Optional[str] = None         # Emoji or icon name
    category: Optional[str] = None     # "Healthcare", "Legal", "Marketing"

    # Workflow type - determines UI and behavior
    workflow_type: WorkflowType = WorkflowType.TEAM_WORKFLOW

    # Workflow structure
    stages: List[Stage]
    triggers: List[WorkflowTrigger]

    # Settings
    enabled: bool = True
    allow_manual_creation: bool = True
    require_approval_to_start: bool = False

    # Metadata
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    # Tags for organization
    tags: List[str] = []


# ============================================
# WORK ITEMS (Instances)
# ============================================

class StageTransition(BaseModel):
    """Record of stage change"""
    from_stage_id: Optional[str] = None  # None if first stage
    to_stage_id: str
    transitioned_at: datetime = Field(default_factory=datetime.utcnow)
    transitioned_by: Optional[str] = None  # User ID or "system"
    notes: Optional[str] = None
    duration_seconds: Optional[int] = None  # Time spent in previous stage


class WorkItemAttachment(BaseModel):
    """File attached to work item"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class WorkItem(BaseModel):
    """Instance of work flowing through a workflow"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    workflow_name: str                 # Denormalized for display

    # Current state
    current_stage_id: str
    current_stage_name: str            # Denormalized
    status: WorkItemStatus
    priority: WorkItemPriority = WorkItemPriority.NORMAL

    # Assignment
    assigned_to: Optional[str] = None  # User ID
    claimed_at: Optional[datetime] = None

    # Data payload (flexible JSON)
    data: Dict[str, Any] = {}

    # Metadata
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # History
    history: List[StageTransition] = []

    # Attachments
    attachments: List[WorkItemAttachment] = []

    # SLA tracking
    sla_due_at: Optional[datetime] = None
    is_overdue: bool = False

    # Tags
    tags: List[str] = []

    # Reference number (human-friendly ID)
    reference_number: Optional[str] = None


# ============================================
# QUEUE MANAGEMENT
# ============================================

class QueueFilter(BaseModel):
    """Filter for queue items"""
    field: str
    operator: ConditionOperator
    value: Any


class Queue(BaseModel):
    """Queue of work items for a role/stage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # "Triage Queue", "Attorney Review"
    stage_id: str
    role_name: Optional[str] = None

    # Filtering
    filters: List[QueueFilter] = []

    # Sorting
    sort_by: Literal["priority", "age", "sla", "custom"] = "priority"
    sort_order: Literal["asc", "desc"] = "desc"

    # Display
    columns: List[str] = ["reference_number", "priority", "age", "status"]

    # Auto-assignment
    enable_auto_assignment: bool = False
    max_items_per_user: Optional[int] = None


# ============================================
# NOTIFICATIONS
# ============================================

class NotificationEvent(str, Enum):
    """Events that trigger notifications"""
    WORK_ITEM_ASSIGNED = "work_item_assigned"
    WORK_ITEM_CLAIMED = "work_item_claimed"
    WORK_ITEM_COMPLETED = "work_item_completed"
    WORK_ITEM_OVERDUE = "work_item_overdue"
    STAGE_ENTERED = "stage_entered"
    APPROVAL_REQUESTED = "approval_requested"
    COMMENT_ADDED = "comment_added"


class Notification(BaseModel):
    """Notification for user"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event: NotificationEvent
    work_item_id: str
    work_item_reference: str
    title: str
    message: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Action
    action_url: Optional[str] = None


# ============================================
# ROLES & PERMISSIONS
# ============================================

class WorkflowRole(BaseModel):
    """Role definition for workflow access"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                          # "Nurse", "Attorney", "Designer"
    description: Optional[str] = None

    # Permissions
    can_create_work_items: bool = True
    can_claim_from_queue: bool = True
    can_reassign: bool = False
    can_cancel: bool = False
    can_view_all: bool = False         # See all work items in workflow

    # Stage access
    accessible_stage_ids: List[str] = []  # Empty = all stages


class UserRoleAssignment(BaseModel):
    """Assign role to user"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role_id: str
    role_name: str                     # Denormalized
    workflow_id: Optional[str] = None  # None = global role

    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: str


# ============================================
# ANALYTICS & METRICS
# ============================================

class WorkflowMetrics(BaseModel):
    """Performance metrics for workflow"""
    workflow_id: str
    workflow_name: str

    # Volume
    total_items_created: int = 0
    total_items_completed: int = 0
    total_items_cancelled: int = 0
    total_items_active: int = 0

    # Performance
    avg_completion_time_minutes: Optional[float] = None
    median_completion_time_minutes: Optional[float] = None
    sla_compliance_rate: Optional[float] = None  # Percentage

    # Bottlenecks
    slowest_stage_id: Optional[str] = None
    slowest_stage_avg_minutes: Optional[float] = None

    # Period
    period_start: datetime
    period_end: datetime

    # Per-stage metrics
    stage_metrics: Dict[str, Dict[str, Any]] = {}


class StageMetrics(BaseModel):
    """Performance metrics for a stage"""
    stage_id: str
    stage_name: str

    # Volume
    items_entered: int = 0
    items_completed: int = 0
    items_currently_in_stage: int = 0

    # Performance
    avg_time_in_stage_minutes: Optional[float] = None
    median_time_in_stage_minutes: Optional[float] = None

    # SLA
    sla_violations: int = 0
    sla_compliance_rate: Optional[float] = None


# ============================================
# P2P SYNC MODELS
# ============================================

class WorkflowSyncMessage(BaseModel):
    """Message for P2P workflow state sync"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: Literal[
        "work_item_created",
        "work_item_claimed",
        "work_item_completed",
        "stage_transition",
        "queue_update",
        "workflow_updated"
    ]

    # Source
    sender_peer_id: str
    sender_user_id: str

    # Payload
    work_item_id: Optional[str] = None
    workflow_id: Optional[str] = None
    payload: Dict[str, Any]

    # Sync tracking
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    vector_clock: Optional[Dict[str, int]] = None  # For CRDT

    # Phase 4: Team isolation and security
    team_id: Optional[str] = None  # Team context for this message
    signature: str = ""  # HMAC signature for team messages


class WorkItemConflict(BaseModel):
    """Conflict detected during P2P sync"""
    work_item_id: str
    conflicting_field: str
    local_value: Any
    remote_value: Any
    local_timestamp: datetime
    remote_timestamp: datetime
    resolution: Optional[Literal["local_wins", "remote_wins", "manual"]] = None


# ============================================
# API REQUEST/RESPONSE MODELS
# ============================================

class CreateWorkItemRequest(BaseModel):
    """Request to create a new work item"""
    workflow_id: str
    data: Dict[str, Any]
    priority: Optional[WorkItemPriority] = None
    tags: Optional[List[str]] = None


class ClaimWorkItemRequest(BaseModel):
    """Request to claim a work item"""
    work_item_id: str
    user_id: str


class CompleteStageRequest(BaseModel):
    """Request to complete current stage"""
    work_item_id: str
    stage_id: str
    data: Dict[str, Any]
    next_stage_id: Optional[str] = None
    notes: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow"""
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None  # Defaults to TEAM_WORKFLOW if not provided
    stages: List[Any]  # Will be converted to Stage objects
    triggers: List[Any]  # Will be converted to WorkflowTrigger objects
