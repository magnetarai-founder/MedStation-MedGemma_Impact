/**
 * Universal Workflow Data Models (Frontend)
 * Industry-agnostic abstractions for distributed work orchestration
 */

// ============================================
// ENUMS
// ============================================

export enum WorkflowTriggerType {
  MANUAL = 'manual',
  FORM_SUBMISSION = 'form',
  SCHEDULE = 'schedule',
  WEBHOOK = 'webhook',
  EMAIL = 'email',
  FILE_UPLOAD = 'file_upload',
  EVENT = 'event',
}

export enum StageType {
  HUMAN = 'human',
  AUTOMATION = 'automation',
  HYBRID = 'hybrid',
  AI = 'ai',
  APPROVAL = 'approval',
}

export enum WorkItemStatus {
  PENDING = 'pending',
  CLAIMED = 'claimed',
  IN_PROGRESS = 'in_progress',
  WAITING = 'waiting',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed',
}

export enum WorkItemPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum AssignmentType {
  ROLE = 'role',
  SPECIFIC_USER = 'user',
  QUEUE = 'queue',
  AUTOMATION = 'automation',
  ROUND_ROBIN = 'round_robin',
}

export enum ConditionOperator {
  EQUALS = '==',
  NOT_EQUALS = '!=',
  GREATER_THAN = '>',
  LESS_THAN = '<',
  CONTAINS = 'contains',
  NOT_CONTAINS = 'not_contains',
  IS_TRUE = 'is_true',
  IS_FALSE = 'is_false',
}

export enum FieldType {
  TEXT = 'text',
  TEXTAREA = 'textarea',
  NUMBER = 'number',
  DATE = 'date',
  TIME = 'time',
  DATETIME = 'datetime',
  SELECT = 'select',
  MULTISELECT = 'multiselect',
  CHECKBOX = 'checkbox',
  RADIO = 'radio',
  FILE_UPLOAD = 'file_upload',
  EMAIL = 'email',
  PHONE = 'phone',
  URL = 'url',
}

export enum NotificationEvent {
  WORK_ITEM_ASSIGNED = 'work_item_assigned',
  WORK_ITEM_CLAIMED = 'work_item_claimed',
  WORK_ITEM_COMPLETED = 'work_item_completed',
  WORK_ITEM_OVERDUE = 'work_item_overdue',
  STAGE_ENTERED = 'stage_entered',
  APPROVAL_REQUESTED = 'approval_requested',
  COMMENT_ADDED = 'comment_added',
}

// ============================================
// FORM DEFINITIONS
// ============================================

export interface FormFieldOption {
  value: string
  label: string
}

export interface FormField {
  id: string
  name: string
  label: string
  type: FieldType
  required?: boolean
  placeholder?: string
  help_text?: string
  default_value?: any

  // Validation
  min_length?: number
  max_length?: number
  min_value?: number
  max_value?: number
  pattern?: string

  // Options
  options?: FormFieldOption[]

  // Conditional
  show_if?: Record<string, any>
}

export interface FormDefinition {
  id: string
  name: string
  description?: string
  fields: FormField[]
  submit_button_text?: string
}

// ============================================
// ROUTING & CONDITIONS
// ============================================

export interface RoutingCondition {
  field: string
  operator: ConditionOperator
  value: any
}

export interface ConditionalRoute {
  id: string
  next_stage_id: string
  conditions?: RoutingCondition[]
  notify?: boolean
  description?: string
}

// ============================================
// AUTOMATION CONFIG
// ============================================

export interface AutomationConfig {
  type: 'n8n' | 'local_ai' | 'custom'

  // For n8n
  n8n_workflow_id?: string
  n8n_webhook_url?: string

  // For local AI
  ai_model?: string
  ai_prompt_template?: string

  // For custom
  custom_script_path?: string

  // Parameters
  parameters?: Record<string, any>

  // Timeout
  timeout_seconds?: number
}

// ============================================
// WORKFLOW STAGES
// ============================================

export interface Stage {
  id: string
  name: string
  description?: string
  stage_type: StageType

  // Assignment
  assignment_type: AssignmentType
  role_name?: string
  assigned_user_id?: string

  // Data collection
  form?: FormDefinition

  // Automation
  automation?: AutomationConfig

  // Business rules
  sla_minutes?: number
  requires_approval?: boolean
  auto_advance?: boolean

  // Routing
  next_stages: ConditionalRoute[]

  // Notifications
  notify_on_arrival?: boolean
  notify_on_overdue?: boolean

  // AI assistance
  ai_suggestions_enabled?: boolean
  ai_suggestion_prompt?: string

  // Metadata
  order?: number
  color?: string
}

// ============================================
// WORKFLOW DEFINITION
// ============================================

export interface WorkflowTrigger {
  id: string
  trigger_type: WorkflowTriggerType

  // For different trigger types
  form_id?: string
  cron_expression?: string
  webhook_url?: string
  email_address?: string
  email_filter?: Record<string, any>

  enabled?: boolean
}

export interface Workflow {
  id: string
  name: string
  description?: string
  icon?: string
  category?: string

  // Structure
  stages: Stage[]
  triggers: WorkflowTrigger[]

  // Settings
  enabled?: boolean
  allow_manual_creation?: boolean
  require_approval_to_start?: boolean

  // Metadata
  created_by: string
  created_at: string
  updated_at: string
  version?: number

  // Organization
  tags?: string[]
}

// ============================================
// WORK ITEMS (Instances)
// ============================================

export interface StageTransition {
  from_stage_id?: string
  to_stage_id: string
  transitioned_at: string
  transitioned_by?: string
  notes?: string
  duration_seconds?: number
}

export interface WorkItemAttachment {
  id: string
  filename: string
  file_path: string
  file_size: number
  mime_type: string
  uploaded_by: string
  uploaded_at: string
}

export interface WorkItem {
  id: string
  workflow_id: string
  workflow_name: string

  // Current state
  current_stage_id: string
  current_stage_name: string
  status: WorkItemStatus
  priority: WorkItemPriority

  // Assignment
  assigned_to?: string
  claimed_at?: string

  // Data
  data: Record<string, any>

  // Metadata
  created_by: string
  created_at: string
  updated_at: string
  completed_at?: string

  // History
  history: StageTransition[]

  // Attachments
  attachments: WorkItemAttachment[]

  // SLA
  sla_due_at?: string
  is_overdue?: boolean

  // Tags
  tags?: string[]

  // Reference
  reference_number?: string
}

// ============================================
// QUEUE MANAGEMENT
// ============================================

export interface QueueFilter {
  field: string
  operator: ConditionOperator
  value: any
}

export interface Queue {
  id: string
  name: string
  stage_id: string
  role_name?: string

  // Filtering
  filters?: QueueFilter[]

  // Sorting
  sort_by?: 'priority' | 'age' | 'sla' | 'custom'
  sort_order?: 'asc' | 'desc'

  // Display
  columns?: string[]

  // Auto-assignment
  enable_auto_assignment?: boolean
  max_items_per_user?: number
}

// ============================================
// NOTIFICATIONS
// ============================================

export interface Notification {
  id: string
  user_id: string
  event: NotificationEvent
  work_item_id: string
  work_item_reference: string
  title: string
  message: string
  read?: boolean
  created_at: string

  // Action
  action_url?: string
}

// ============================================
// ROLES & PERMISSIONS
// ============================================

export interface WorkflowRole {
  id: string
  name: string
  description?: string

  // Permissions
  can_create_work_items?: boolean
  can_claim_from_queue?: boolean
  can_reassign?: boolean
  can_cancel?: boolean
  can_view_all?: boolean

  // Stage access
  accessible_stage_ids?: string[]
}

export interface UserRoleAssignment {
  id: string
  user_id: string
  role_id: string
  role_name: string
  workflow_id?: string

  assigned_at: string
  assigned_by: string
}

// ============================================
// ANALYTICS & METRICS
// ============================================

export interface WorkflowMetrics {
  workflow_id: string
  workflow_name: string

  // Volume
  total_items_created: number
  total_items_completed: number
  total_items_cancelled: number
  total_items_active: number

  // Performance
  avg_completion_time_minutes?: number
  median_completion_time_minutes?: number
  sla_compliance_rate?: number

  // Bottlenecks
  slowest_stage_id?: string
  slowest_stage_avg_minutes?: number

  // Period
  period_start: string
  period_end: string

  // Per-stage
  stage_metrics: Record<string, Record<string, any>>
}

export interface StageMetrics {
  stage_id: string
  stage_name: string

  // Volume
  items_entered: number
  items_completed: number
  items_currently_in_stage: number

  // Performance
  avg_time_in_stage_minutes?: number
  median_time_in_stage_minutes?: number

  // SLA
  sla_violations: number
  sla_compliance_rate?: number
}

// ============================================
// P2P SYNC MODELS
// ============================================

export type WorkflowSyncMessageType =
  | 'work_item_created'
  | 'work_item_claimed'
  | 'work_item_completed'
  | 'stage_transition'
  | 'queue_update'
  | 'workflow_updated'

export interface WorkflowSyncMessage {
  message_id: string
  message_type: WorkflowSyncMessageType

  // Source
  sender_peer_id: string
  sender_user_id: string

  // Payload
  work_item_id?: string
  workflow_id?: string
  payload: Record<string, any>

  // Sync tracking
  timestamp: string
  vector_clock?: Record<string, number>
}

export interface WorkItemConflict {
  work_item_id: string
  conflicting_field: string
  local_value: any
  remote_value: any
  local_timestamp: string
  remote_timestamp: string
  resolution?: 'local_wins' | 'remote_wins' | 'manual'
}

// ============================================
// API REQUEST/RESPONSE TYPES
// ============================================

export interface CreateWorkItemRequest {
  workflow_id: string
  data: Record<string, any>
  priority?: WorkItemPriority
  tags?: string[]
}

export interface ClaimWorkItemRequest {
  work_item_id: string
  user_id: string
}

export interface CompleteStageRequest {
  work_item_id: string
  stage_id: string
  data: Record<string, any>
  next_stage_id?: string
  notes?: string
}

export interface CreateWorkflowRequest {
  name: string
  description?: string
  icon?: string
  category?: string
  stages: Omit<Stage, 'id'>[]
  triggers: Omit<WorkflowTrigger, 'id'>[]
}

// ============================================
// UI STATE TYPES
// ============================================

export interface QueueViewState {
  selected_queue_id?: string
  selected_work_item_id?: string
  filters: QueueFilter[]
  sort_by: 'priority' | 'age' | 'sla'
  sort_order: 'asc' | 'desc'
  view_mode: 'list' | 'kanban' | 'table'
}

export interface WorkflowBuilderState {
  workflow_id?: string
  stages: Stage[]
  selected_stage_id?: string
  is_editing: boolean
  has_unsaved_changes: boolean
}

// ============================================
// UTILITY TYPES
// ============================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface WorkflowStatistics {
  total_workflows: number
  active_workflows: number
  total_work_items: number
  items_in_progress: number
  items_completed_today: number
  avg_completion_time_hours: number
  sla_compliance_rate: number
}
