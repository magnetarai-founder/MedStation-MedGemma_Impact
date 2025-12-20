//
//  KanbanService.swift
//  MagnetarStudio
//
//  Service for connecting Kanban workspace to backend API
//

import Foundation

// MARK: - Models

struct KanbanBoardAPI: Codable, Identifiable {
    let boardId: String
    let projectId: String
    let name: String
    let createdAt: String

    var id: String { boardId }

    enum CodingKeys: String, CodingKey {
        case boardId = "board_id"
        case projectId = "project_id"
        case name
        case createdAt = "created_at"
    }
}

struct KanbanTaskAPI: Codable, Identifiable {
    let taskId: String
    let boardId: String
    let columnId: String
    let title: String
    let description: String?
    let status: String?
    let assigneeId: String?
    let priority: String?
    let dueDate: String?
    let tags: [String]
    let position: Double
    let createdAt: String
    let updatedAt: String

    var id: String { taskId }

    enum CodingKeys: String, CodingKey {
        case taskId = "task_id"
        case boardId = "board_id"
        case columnId = "column_id"
        case title, description, status
        case assigneeId = "assignee_id"
        case priority
        case dueDate = "due_date"
        case tags, position
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

// MARK: - Service

@MainActor
class KanbanService {
    static let shared = KanbanService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Boards

    func listBoards(projectId: String) async throws -> [KanbanBoardAPI] {
        try await apiClient.request(
            path: "/v1/kanban/projects/\(projectId)/boards",
            method: .get
        )
    }

    func createBoard(projectId: String, name: String) async throws -> KanbanBoardAPI {
        return try await apiClient.request(
            path: "/v1/kanban/boards",
            method: .post,
            jsonBody: ["project_id": projectId, "name": name]
        )
    }

    func deleteBoard(boardId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/kanban/boards/\(boardId)",
            method: .delete
        )
    }

    // MARK: - Tasks

    func listTasks(boardId: String, columnId: String? = nil) async throws -> [KanbanTaskAPI] {
        var path = "/v1/kanban/boards/\(boardId)/tasks"
        if let columnId = columnId {
            path += "?column_id=\(columnId)"
        }
        return try await apiClient.request(path: path, method: .get)
    }

    func createTask(
        boardId: String,
        columnId: String,
        title: String,
        description: String? = nil,
        status: String? = nil,
        assigneeId: String? = nil,
        priority: String? = nil,
        dueDate: String? = nil,
        tags: [String]? = nil
    ) async throws -> KanbanTaskAPI {
        var jsonBody: [String: Any] = [
            "board_id": boardId,
            "column_id": columnId,
            "title": title
        ]
        if let description = description { jsonBody["description"] = description }
        if let status = status { jsonBody["status"] = status }
        if let assigneeId = assigneeId { jsonBody["assignee_id"] = assigneeId }
        if let priority = priority { jsonBody["priority"] = priority }
        if let dueDate = dueDate { jsonBody["due_date"] = dueDate }
        if let tags = tags { jsonBody["tags"] = tags }

        return try await apiClient.request(
            path: "/v1/kanban/tasks",
            method: .post,
            jsonBody: jsonBody
        )
    }

    func deleteTask(taskId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/kanban/tasks/\(taskId)",
            method: .delete
        )
    }

    func updateTask(
        taskId: String,
        title: String? = nil,
        description: String? = nil,
        status: String? = nil,
        columnId: String? = nil,
        priority: String? = nil,
        assigneeId: String? = nil
    ) async throws -> KanbanTaskAPI {
        var jsonBody: [String: Any] = [:]
        if let title = title { jsonBody["title"] = title }
        if let description = description { jsonBody["description"] = description }
        if let status = status { jsonBody["status"] = status }
        if let columnId = columnId { jsonBody["column_id"] = columnId }
        if let priority = priority { jsonBody["priority"] = priority }
        if let assigneeId = assigneeId { jsonBody["assignee_id"] = assigneeId }

        return try await apiClient.request(
            path: "/v1/kanban/tasks/\(taskId)",
            method: .patch,
            jsonBody: jsonBody
        )
    }
}
