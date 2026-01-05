//
//  KanbanStore.swift
//  MagnetarStudio
//
//  Store for Kanban workspace state and operations
//

import Foundation
import Observation

// Static formatter for date parsing (expensive to create)
private let iso8601Formatter: ISO8601DateFormatter = {
    let formatter = ISO8601DateFormatter()
    return formatter
}()

/// Kanban workspace state and operations
@MainActor
@Observable
final class KanbanStore {
    static let shared = KanbanStore()

    // MARK: - State Persistence Keys
    private static let selectedBoardIdKey = "kanban.selectedBoardId"

    // MARK: - Observable State

    var boards: [KanbanBoardAPI] = []
    var tasks: [KanbanTaskAPI] = []
    var selectedBoardId: String? {
        didSet { UserDefaults.standard.set(selectedBoardId, forKey: Self.selectedBoardIdKey) }
    }
    var isLoading = false
    var error: String?

    private let service = KanbanService.shared

    private init() {
        // Restore persisted state
        self.selectedBoardId = UserDefaults.standard.string(forKey: Self.selectedBoardIdKey)
    }

    // MARK: - Board Management

    func loadBoards(projectId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            boards = try await service.listBoards(projectId: projectId)
            error = nil
        } catch {
            self.error = "Failed to load boards: \(error.localizedDescription)"
        }
    }

    func createBoard(projectId: String, name: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newBoard = try await service.createBoard(projectId: projectId, name: name)
            boards.insert(newBoard, at: 0)
            error = nil
        } catch {
            self.error = "Failed to create board: \(error.localizedDescription)"
        }
    }

    func deleteBoard(boardId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await service.deleteBoard(boardId: boardId)
            boards.removeAll { $0.boardId == boardId }
            if selectedBoardId == boardId {
                selectedBoardId = nil
                tasks = []
            }
            error = nil
        } catch {
            self.error = "Failed to delete board: \(error.localizedDescription)"
        }
    }

    // MARK: - Task Management

    func loadTasks(boardId: String, columnId: String? = nil) async {
        isLoading = true
        defer { isLoading = false }

        do {
            tasks = try await service.listTasks(boardId: boardId, columnId: columnId)
            selectedBoardId = boardId
            error = nil
        } catch {
            self.error = "Failed to load tasks: \(error.localizedDescription)"
        }
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
    ) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newTask = try await service.createTask(
                boardId: boardId,
                columnId: columnId,
                title: title,
                description: description,
                status: status,
                assigneeId: assigneeId,
                priority: priority,
                dueDate: dueDate,
                tags: tags
            )
            tasks.append(newTask)
            error = nil
        } catch {
            self.error = "Failed to create task: \(error.localizedDescription)"
        }
    }

    func updateTask(
        taskId: String,
        title: String? = nil,
        description: String? = nil,
        status: String? = nil,
        columnId: String? = nil,
        priority: String? = nil,
        assigneeId: String? = nil
    ) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let updatedTask = try await service.updateTask(
                taskId: taskId,
                title: title,
                description: description,
                status: status,
                columnId: columnId,
                priority: priority,
                assigneeId: assigneeId
            )

            if let index = tasks.firstIndex(where: { $0.taskId == taskId }) {
                tasks[index] = updatedTask
            }
            error = nil
        } catch {
            self.error = "Failed to update task: \(error.localizedDescription)"
        }
    }

    func deleteTask(taskId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await service.deleteTask(taskId: taskId)
            tasks.removeAll { $0.taskId == taskId }
            error = nil
        } catch {
            self.error = "Failed to delete task: \(error.localizedDescription)"
        }
    }

    func moveTask(taskId: String, toColumnId: String) async {
        await updateTask(taskId: taskId, columnId: toColumnId)
    }

    // MARK: - Helpers

    /// Group tasks by column for board view
    func tasksByColumn() -> [String: [KanbanTaskAPI]] {
        Dictionary(grouping: tasks) { $0.columnId }
    }

    /// Get tasks filtered by status
    func tasks(withStatus status: String) -> [KanbanTaskAPI] {
        tasks.filter { $0.status == status }
    }

    /// Get tasks assigned to a specific user
    func tasks(assignedTo userId: String) -> [KanbanTaskAPI] {
        tasks.filter { $0.assigneeId == userId }
    }

    /// Get overdue tasks
    func overdueTasks() -> [KanbanTaskAPI] {
        let now = Date()

        return tasks.filter { task in
            guard let dueDateStr = task.dueDate,
                  let dueDate = iso8601Formatter.date(from: dueDateStr) else {
                return false
            }
            return dueDate < now
        }
    }

    /// Get high priority tasks
    func highPriorityTasks() -> [KanbanTaskAPI] {
        tasks.filter { $0.priority == "high" || $0.priority == "urgent" }
    }
}
