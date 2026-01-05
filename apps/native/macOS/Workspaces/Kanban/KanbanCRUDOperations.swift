//
//  KanbanCRUDOperations.swift
//  MagnetarStudio (macOS)
//
//  View-layer CRUD adapter - delegates to KanbanStore and converts to UI models.
//  Extracted from KanbanWorkspace.swift (Phase 6.20)
//  Consolidated to use KanbanStore.shared as single source of truth.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "KanbanCRUD")

@MainActor
@Observable
class KanbanCRUDOperations {
    /// Current project ID - delegates to KanbanStore's configurable setting
    var currentProjectId: String { store.currentProjectId }

    /// Error message from last operation
    var errorMessage: String? { store.error }

    private let store = KanbanStore.shared

    // MARK: - Board Operations

    func createBoard(name: String) async -> KanbanBoard? {
        guard !name.isEmpty else { return nil }

        // Create through the shared store
        await store.createBoard(projectId: currentProjectId, name: name)

        // Check if creation succeeded
        guard store.error == nil,
              let apiBoard = store.boards.first(where: { $0.name == name }) else {
            logger.error("Failed to create board: \(self.store.error ?? "Unknown error")")
            return nil
        }

        // Convert to UI model
        return KanbanBoard(
            name: apiBoard.name,
            icon: "folder",
            taskCount: 0,
            boardId: apiBoard.boardId
        )
    }

    func deleteBoard(_ board: KanbanBoard) async -> Bool {
        guard let boardId = board.boardId else {
            logger.warning("Cannot delete board: no backend ID")
            return false
        }

        // Delete through the shared store
        await store.deleteBoard(boardId: boardId)

        // Return false if there was an error (SIMPLE-C3 fix)
        if store.error != nil {
            logger.error("Failed to delete board: \(self.store.error ?? "Unknown error")")
            return false
        }

        return true
    }

    // MARK: - Task Operations

    func createTask(title: String, board: KanbanBoard) async -> KanbanTask? {
        guard !title.isEmpty else { return nil }
        guard let boardId = board.boardId else {
            logger.warning("Cannot create task: board has no backend ID")
            return nil
        }

        // For now, use "todo" as the default column_id
        let defaultColumnId = "todo"

        // Create through the shared store
        await store.createTask(
            boardId: boardId,
            columnId: defaultColumnId,
            title: title,
            description: "New task description",
            status: "todo",
            priority: "medium"
        )

        // Check if creation succeeded
        guard store.error == nil,
              let apiTask = store.tasks.first(where: { $0.title == title }) else {
            logger.error("Failed to create task: \(self.store.error ?? "Unknown error")")
            return nil
        }

        // Convert to UI model
        return KanbanTask(
            title: apiTask.title,
            description: apiTask.description ?? "",
            status: TaskStatus(apiString: apiTask.status ?? "todo"),
            priority: TaskPriority(apiString: apiTask.priority ?? "medium"),
            assignee: apiTask.assigneeId ?? "Unassigned",
            dueDate: apiTask.dueDate ?? "TBD",
            labels: apiTask.tags,
            taskId: apiTask.taskId,
            boardId: apiTask.boardId,
            columnId: apiTask.columnId
        )
    }

    func deleteTask(_ task: KanbanTask) async -> Bool {
        guard let taskId = task.taskId else {
            logger.warning("Cannot delete task: no backend ID")
            return false
        }

        // Delete through the shared store
        await store.deleteTask(taskId: taskId)

        // Return false if there was an error (SIMPLE-C3 fix)
        if store.error != nil {
            logger.error("Failed to delete task: \(self.store.error ?? "Unknown error")")
            return false
        }

        return true
    }
}
