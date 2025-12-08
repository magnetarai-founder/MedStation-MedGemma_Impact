//
//  AgentModels.swift
//  MagnetarStudio
//
//  Models for Agent API integration
//  Matches backend /api/v1/agent/* endpoint schemas
//
//  Part of Noah's Ark for the Digital Age - Agent integration
//

import Foundation

// MARK: - Route Request/Response

/// Request to route user input and determine intent
struct AgentRouteRequest: Codable {
    let input: String
    let session_id: String?

    init(input: String, session_id: String? = nil) {
        self.input = input
        self.session_id = session_id
    }
}

/// Response from route endpoint with intent classification
struct AgentRouteResponse: Codable {
    let intent: String              // "code_edit", "shell", "question"
    let confidence: Float           // 0.0-1.0
    let model_hint: String?         // Suggested model (e.g., "qwen2.5-coder:32b")
    let next_action: String         // "call /agent/plan" or "answer directly"
    let learning_used: Bool?        // Whether learning system influenced decision
}

// MARK: - Plan Request/Response

/// Request to generate execution plan
struct AgentPlanRequest: Codable {
    let input: String
    let context_bundle: AgentContextBundle?
    let session_id: String?
}

/// Execution plan step
struct AgentPlanStep: Codable {
    let step_number: Int
    let action: String
    let description: String
    let estimated_time_min: Int
}

/// Response with generated plan
struct AgentPlanResponse: Codable {
    let steps: [AgentPlanStep]
    let estimated_time_min: Int
    let risks: [String]
    let requires_confirmation: Bool
}

// MARK: - Context Request/Response

/// Request for context bundle
struct AgentContextRequest: Codable {
    let repo_root: String
    let session_id: String?
}

/// Context bundle response
struct AgentContextResponse: Codable {
    let relevant_files: [String]?
    let git_info: AgentGitInfo?
    let project_structure: String?
}

struct AgentGitInfo: Codable {
    let branch: String
    let has_uncommitted_changes: Bool
    let recent_commits: [String]
}

// MARK: - Context Bundle (for sending to backend)

/// Context bundle to include with requests
struct AgentContextBundle: Codable {
    let vault_context: VaultContextData?
    let data_context: DataContextData?
    let kanban_context: KanbanContextData?
    let workflow_context: WorkflowContextData?
    let team_context: TeamContextData?
    let code_context: CodeContextData?
    let system_resources: SystemResourceData?
}

struct VaultContextData: Codable {
    let file_count: Int
    let total_size_mb: Int
}

struct DataContextData: Codable {
    let loaded_tables: [String]
    let recent_queries: [String]
}

struct KanbanContextData: Codable {
    let active_tasks: Int
    let current_board: String?
}

struct WorkflowContextData: Codable {
    let running_workflows: Int
    let recent_executions: [String]
}

struct TeamContextData: Codable {
    let active_channels: Int
    let recent_documents: [String]
}

struct CodeContextData: Codable {
    let open_files: [String]
    let current_branch: String?
}

struct SystemResourceData: Codable {
    let available_memory_gb: Float
    let cpu_usage: Float
    let thermal_state: String
}

// MARK: - Apply Request/Response

/// Request to apply a plan
struct AgentApplyRequest: Codable {
    let input: String
    let repo_root: String
    let model: String?
    let dry_run: Bool
    let session_id: String?
}

/// Apply response with patches
struct AgentApplyResponse: Codable {
    let success: Bool
    let patches: [AgentPatch]
    let summary: String
    let patch_id: String
}

struct AgentPatch: Codable {
    let file_path: String
    let diff: String
    let status: String  // "created", "modified", "deleted"
}

// MARK: - Capabilities Response

/// System capabilities response
struct AgentCapabilitiesResponse: Codable {
    let engines: [String: AgentEngineStatus]
}

struct AgentEngineStatus: Codable {
    let available: Bool
    let message: String
}

// MARK: - Session Models

/// Agent session
struct AgentSession: Codable, Identifiable {
    let id: String
    let user_id: String
    let repo_root: String
    let status: String  // "active", "archived"
    let created_at: String
    let last_activity_at: String
    let attached_work_item_id: String?
    let current_plan: AgentPlanResponse?
}

struct AgentSessionCreateRequest: Codable {
    let repo_root: String
    let attached_work_item_id: String?
}

// Note: Context Search models are defined in ContextService.swift
