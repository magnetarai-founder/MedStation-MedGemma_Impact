//
//  KanbanCRUDOperations.swift
//  MagnetarStudio (macOS)
//
//  CRUD operations manager - Extracted from KanbanWorkspace.swift (Phase 6.20)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "KanbanCRUD")

@MainActor
@Observable
class KanbanCRUDOperations {
    private let defaultProjectId = "default"

    // MARK: - Board Operations

    func createBoard(name: String) async -> KanbanBoard? {
        guard !name.isEmpty else { return nil }

        do {
            // Create board via API
            let apiBoard = try await KanbanService.shared.createBoard(
                projectId: defaultProjectId,
                name: name
            )

            return KanbanBoard(
                name: apiBoard.name,
                icon: "folder",
                taskCount: 0,
                boardId: apiBoard.boardId
            )
        } catch {
            logger.error("Failed to create board: \(error.localizedDescription)")
            // Fall back to local-only creation
            return KanbanBoard(
                name: name,
                icon: "folder",
                taskCount: 0,
                boardId: nil
            )
        }
    }

    func deleteBoard(_ board: KanbanBoard) async -> Bool {
        do {
            // Delete from API if we have a backend ID
            if let boardId = board.boardId {
                try await KanbanService.shared.deleteBoard(boardId: boardId)
            }
            return true
        } catch {
            logger.warning("Failed to delete board from API: \(error.localizedDescription)")
            // Still return true to remove locally even if API fails
            return true
        }
    }

    // MARK: - Task Operations

    func createTask(title: String, board: KanbanBoard) async -> KanbanTask? {
        guard !title.isEmpty else { return nil }
        guard let boardId = board.boardId else {
            logger.warning("Cannot create task: board has no backend ID")
            return nil
        }

        do {
            // For now, use "todo" as the default column_id
            // In a full implementation, we'd fetch columns and use the first one
            let defaultColumnId = "todo"

            let apiTask = try await KanbanService.shared.createTask(
                boardId: boardId,
                columnId: defaultColumnId,
                title: title,
                description: "New task description",
                status: "todo",
                priority: "medium"
            )

            return KanbanTask(
                title: apiTask.title,
                description: apiTask.description ?? "",
                status: taskStatusFromString(apiTask.status ?? "todo"),
                priority: taskPriorityFromString(apiTask.priority ?? "medium"),
                assignee: apiTask.assigneeId ?? "Unassigned",
                dueDate: apiTask.dueDate ?? "TBD",
                labels: apiTask.tags,
                taskId: apiTask.taskId,
                boardId: apiTask.boardId,
                columnId: apiTask.columnId
            )
        } catch {
            logger.error("Failed to create task: \(error.localizedDescription)")
            // Fall back to local-only creation
            return KanbanTask(
                title: title,
                description: "New task description",
                status: .todo,
                priority: .medium,
                assignee: "Unassigned",
                dueDate: "TBD",
                labels: [],
                taskId: nil,
                boardId: nil,
                columnId: nil
            )
        }
    }

    func deleteTask(_ task: KanbanTask) async -> Bool {
        do {
            // Delete from API if we have a backend ID
            if let taskId = task.taskId {
                try await KanbanService.shared.deleteTask(taskId: taskId)
            }
            return true
        } catch {
            logger.warning("Failed to delete task from API: \(error.localizedDescription)")
            // Still return true to remove locally even if API fails
            return true
        }
    }

    // MARK: - Helper Methods

    private func taskStatusFromString(_ str: String) -> TaskStatus {
        switch str.lowercased() {
        case "done": return .done
        case "in_progress", "inprogress": return .inProgress
        default: return .todo
        }
    }

    private func taskPriorityFromString(_ str: String) -> TaskPriority {
        switch str.lowercased() {
        case "high": return .high
        case "low": return .low
        default: return .medium
        }
    }
}
