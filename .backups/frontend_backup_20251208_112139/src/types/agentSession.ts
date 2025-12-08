/**
 * Agent Session Types (Phase C)
 * Stateful workspace sessions for agent operations
 */

export interface AgentSession {
  id: string
  user_id: string
  repo_root: string
  created_at: string
  last_activity_at: string
  status: 'active' | 'completed' | 'archived'
  current_plan: {
    steps?: Array<{
      description: string
      risk_level: string
      estimated_files: number
    }>
    risks?: string[]
    requires_confirmation?: boolean
    estimated_time_min?: number
    model_used?: string
  } | null
  attached_work_item_id: string | null
}

export interface AgentSessionCreateRequest {
  repo_root: string
  attached_work_item_id?: string
}
