import Foundation

// MARK: - Workflow

struct Workflow: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let icon: String?
    let category: String?
    let workflowType: String?     // "local" | "team"
    let visibility: String?        // "personal" | "team" | "global"
    let isTemplate: Bool?
    let stages: [Stage]?
    let triggers: [WorkflowTrigger]?
    let ownerUserId: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case description
        case icon
        case category
        case workflowType = "workflow_type"
        case visibility
        case isTemplate = "is_template"
        case stages
        case triggers
        case ownerUserId = "owner_user_id"
    }
}

// MARK: - Stage

struct Stage: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let stageType: String
    let assignmentType: String
    let order: Int
    let nextStages: [ConditionalRoute]?
    let slaMinutes: Int?
    let roleName: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case description
        case stageType = "stage_type"
        case assignmentType = "assignment_type"
        case order
        case nextStages = "next_stages"
        case slaMinutes = "sla_minutes"
        case roleName = "role_name"
    }
}

// MARK: - Conditional Route

struct ConditionalRoute: Codable, Identifiable {
    let id: String?
    let nextStageId: String
    let conditions: [[String: AnyCodable]]?

    enum CodingKeys: String, CodingKey {
        case id
        case nextStageId = "next_stage_id"
        case conditions
    }

    // Computed ID for Identifiable
    var computedId: String {
        id ?? UUID().uuidString
    }
}

// MARK: - Workflow Trigger

struct WorkflowTrigger: Codable {
    let triggerType: String
    let enabled: Bool?

    enum CodingKeys: String, CodingKey {
        case triggerType = "trigger_type"
        case enabled
    }
}

// MARK: - Work Item

struct WorkItem: Codable, Identifiable {
    let id: String
    let workflowId: String
    let currentStageId: String
    let status: String             // "claimed" | "in_progress" | "completed" | ...
    let priority: String           // "urgent" | "high" | "normal" | "low"
    let data: [String: AnyCodable]
    let referenceNumber: String?
    let currentStageName: String?
    let workflowName: String?
    let isOverdue: Bool?
    let completedAt: String?
    let createdAt: String?
    let tags: [String]?

    enum CodingKeys: String, CodingKey {
        case id
        case workflowId = "workflow_id"
        case currentStageId = "current_stage_id"
        case status
        case priority
        case data
        case referenceNumber = "reference_number"
        case currentStageName = "current_stage_name"
        case workflowName = "workflow_name"
        case isOverdue = "is_overdue"
        case completedAt = "completed_at"
        case createdAt = "created_at"
        case tags
    }
}

// MARK: - Analytics

struct WorkflowAnalytics: Codable {
    let workflowName: String
    let totalItems: Int
    let completedItems: Int
    let inProgressItems: Int
    let averageCycleTimeSeconds: Int?
    let medianCycleTimeSeconds: Int?
    let cancelledItems: Int
    let failedItems: Int
    let stages: [StageAnalytics]?

    enum CodingKeys: String, CodingKey {
        case workflowName = "workflow_name"
        case totalItems = "total_items"
        case completedItems = "completed_items"
        case inProgressItems = "in_progress_items"
        case averageCycleTimeSeconds = "average_cycle_time_seconds"
        case medianCycleTimeSeconds = "median_cycle_time_seconds"
        case cancelledItems = "cancelled_items"
        case failedItems = "failed_items"
        case stages
    }
}

struct StageAnalytics: Codable, Identifiable {
    let stageId: String
    let stageName: String
    let enteredCount: Int
    let completedCount: Int
    let averageTimeSeconds: Int?
    let medianTimeSeconds: Int?

    var id: String { stageId }

    enum CodingKeys: String, CodingKey {
        case stageId = "stage_id"
        case stageName = "stage_name"
        case enteredCount = "entered_count"
        case completedCount = "completed_count"
        case averageTimeSeconds = "average_time_seconds"
        case medianTimeSeconds = "median_time_seconds"
    }
}

// MARK: - Request Models

struct InstantiateTemplateRequest: Codable {
    let name: String
    let description: String?
}

struct SaveWorkflowRequest: Codable {
    let workflowId: String
    let name: String
    let nodes: [[String: AnyCodable]]
    let edges: [[String: AnyCodable]]

    enum CodingKeys: String, CodingKey {
        case workflowId = "workflow_id"
        case name
        case nodes
        case edges
    }
}

struct RunWorkflowRequest: Codable {
    let workflowId: String
    let name: String
    let nodes: [[String: AnyCodable]]
    let edges: [[String: AnyCodable]]

    enum CodingKeys: String, CodingKey {
        case workflowId = "workflow_id"
        case name
        case nodes
        case edges
    }
}

struct ClaimWorkItemRequest: Codable {
    let userId: String
}

struct StartWorkItemRequest: Codable {
    let userId: String
}
