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

struct CreateTaskRequest: Codable {
    let boardId: String
    let columnId: String
    let title: String
    let description: String?
    let status: String?
    let assigneeId: String?
    let priority: String?
    let dueDate: String?
    let tags: [String]?
    let position: Double?

    enum CodingKeys: String, CodingKey {
        case boardId = "board_id"
        case columnId = "column_id"
        case title, description, status
        case assigneeId = "assignee_id"
        case priority
        case dueDate = "due_date"
        case tags, position
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
            "/v1/kanban/projects/\(projectId)/boards",
            method: .get
        )
    }

    func createBoard(projectId: String, name: String) async throws -> KanbanBoardAPI {
        struct CreateBoardRequest: Codable {
            let projectId: String
            let name: String

            enum CodingKeys: String, CodingKey {
                case projectId = "project_id"
                case name
            }
        }

        return try await apiClient.request(
            "/v1/kanban/boards",
            method: .post,
            body: CreateBoardRequest(projectId: projectId, name: name)
        )
    }

    func deleteBoard(boardId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            "/v1/kanban/boards/\(boardId)",
            method: .delete
        )
    }

    // MARK: - Tasks

    func listTasks(boardId: String, columnId: String? = nil) async throws -> [KanbanTaskAPI] {
        var path = "/v1/kanban/boards/\(boardId)/tasks"
        if let columnId = columnId {
            path += "?column_id=\(columnId)"
        }
        return try await apiClient.request(path, method: .get)
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
        let request = CreateTaskRequest(
            boardId: boardId,
            columnId: columnId,
            title: title,
            description: description,
            status: status,
            assigneeId: assigneeId,
            priority: priority,
            dueDate: dueDate,
            tags: tags,
            position: nil
        )

        return try await apiClient.request(
            "/v1/kanban/tasks",
            method: .post,
            body: request
        )
    }

    func deleteTask(taskId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            "/v1/kanban/tasks/\(taskId)",
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
        struct UpdateRequest: Codable {
            let title: String?
            let description: String?
            let status: String?
            let columnId: String?
            let priority: String?
            let assigneeId: String?

            enum CodingKeys: String, CodingKey {
                case title, description, status
                case columnId = "column_id"
                case priority
                case assigneeId = "assignee_id"
            }
        }

        let request = UpdateRequest(
            title: title,
            description: description,
            status: status,
            columnId: columnId,
            priority: priority,
            assigneeId: assigneeId
        )

        return try await apiClient.request(
            "/v1/kanban/tasks/\(taskId)",
            method: .patch,
            body: request
        )
    }
}
