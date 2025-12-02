import Foundation

/// Service layer for Workflow endpoints
final class WorkflowService {
    static let shared = WorkflowService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Workflow Management

    func listWorkflows(type: String) async throws -> [Workflow] {
        try await apiClient.request(
            path: "/v1/workflow/workflows?workflow_type=\(type)",
            method: .get
        )
    }

    func starWorkflow(id: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/workflow/workflows/\(id)/star",
            method: .post,
            jsonBody: [:]
        ) as EmptyResponse
    }

    func unstarWorkflow(id: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/workflow/workflows/\(id)/star",
            method: .delete
        ) as EmptyResponse
    }

    // MARK: - Templates

    func listTemplates() async throws -> [Workflow] {
        try await apiClient.request(
            path: "/v1/workflow/templates",
            method: .get
        )
    }

    func instantiateTemplate(
        id: String,
        name: String,
        description: String? = nil
    ) async throws -> Workflow {
        var payload: [String: Any] = ["name": name]
        if let description = description {
            payload["description"] = description
        }

        return try await apiClient.request(
            path: "/v1/workflow/templates/\(id)/instantiate",
            method: .post,
            jsonBody: payload
        )
    }

    // MARK: - Work Items / Queue

    func getQueue(workflowId: String, role: String? = nil) async throws -> [WorkItem] {
        let path: String
        if let role = role {
            path = "/v1/workflow/workflows/\(workflowId)/work-items?role=\(role)"
        } else {
            path = "/v1/workflow/workflows/\(workflowId)/work-items"
        }

        return try await apiClient.request(
            path: path,
            method: .get
        )
    }

    func getMyWork(workflowId: String) async throws -> [WorkItem] {
        try await apiClient.request(
            path: "/v1/workflow/workflows/\(workflowId)/work-items/my",
            method: .get
        )
    }

    func claimWorkItem(id: String, userId: String) async throws -> WorkItem {
        try await apiClient.request(
            path: "/v1/work-items/\(id)/claim",
            method: .post,
            jsonBody: ["userId": userId]
        )
    }

    func startWorkItem(id: String, userId: String) async throws -> WorkItem {
        try await apiClient.request(
            path: "/v1/work-items/\(id)/start",
            method: .post,
            jsonBody: ["userId": userId]
        )
    }

    // MARK: - Builder (Save/Run)

    func saveWorkflow(
        workflowId: String,
        name: String,
        nodes: [[String: Any]],
        edges: [[String: Any]]
    ) async throws {
        _ = try await apiClient.request(
            path: "/v1/automation/save",
            method: .post,
            jsonBody: [
                "workflow_id": workflowId,
                "name": name,
                "nodes": nodes,
                "edges": edges
            ]
        ) as EmptyResponse
    }

    func runWorkflow(
        workflowId: String,
        name: String,
        nodes: [[String: Any]],
        edges: [[String: Any]]
    ) async throws {
        _ = try await apiClient.request(
            path: "/v1/automation/run",
            method: .post,
            jsonBody: [
                "workflow_id": workflowId,
                "name": name,
                "nodes": nodes,
                "edges": edges
            ]
        ) as EmptyResponse
    }

    // MARK: - Analytics

    func fetchAnalytics(workflowId: String) async throws -> WorkflowAnalytics {
        try await apiClient.request(
            path: "/v1/workflow/workflows/\(workflowId)/analytics",
            method: .get
        )
    }
}
