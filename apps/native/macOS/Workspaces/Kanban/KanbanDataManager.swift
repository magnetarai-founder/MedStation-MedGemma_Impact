//
//  KanbanDataManager.swift
//  MagnetarStudio (macOS)
//
//  View-layer adapter for KanbanStore - converts API models to UI models.
//  Extracted from KanbanWorkspace.swift (Phase 6.20)
//  Consolidated to use KanbanStore.shared as single source of truth.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "KanbanDataManager")

@MainActor
@Observable
class KanbanDataManager {
    /// UI-friendly board models (converted from KanbanStore's API models)
    var boards: [KanbanBoard] = []
    /// UI-friendly task models (converted from KanbanStore's API models)
    var tasks: [KanbanTask] = []

    /// Loading state - delegates to KanbanStore
    var isLoading: Bool { store.isLoading }

    /// Error state - delegates to KanbanStore
    var error: String? { store.error }

    /// Current project ID - delegates to KanbanStore's configurable setting
    var currentProjectId: String { store.currentProjectId }

    private let store = KanbanStore.shared

    // MARK: - Loading (delegates to KanbanStore)

    func loadBoardsAndTasks() async -> KanbanBoard? {
        // Load boards through the shared store
        await store.loadBoards(projectId: currentProjectId)

        // Convert API models to UI models
        boards = store.boards.map { apiBoard in
            KanbanBoard(
                name: apiBoard.name,
                icon: "folder",
                taskCount: 0,  // Would need separate API call to get count
                boardId: apiBoard.boardId
            )
        }

        // If we have boards, load tasks for the first one
        if let firstBoard = store.boards.first {
            await loadTasks(boardId: firstBoard.boardId)
            return boards.first
        }

        return nil
    }

    func loadTasks(boardId: String) async {
        // Load tasks through the shared store
        await store.loadTasks(boardId: boardId)

        // Convert API models to UI models
        tasks = store.tasks.map { apiTask in
            KanbanTask(
                title: apiTask.title,
                description: apiTask.description ?? "",
                status: TaskStatus(apiString: apiTask.status ?? "todo"),
                priority: TaskPriority(apiString: apiTask.priority ?? "medium"),
                assignee: apiTask.assigneeId ?? "Unassigned",
                dueDate: apiTask.dueDate ?? "",
                labels: apiTask.tags,
                taskId: apiTask.taskId,
                boardId: apiTask.boardId,
                columnId: apiTask.columnId
            )
        }
    }

    // MARK: - Refresh (sync UI models from store)

    /// Refresh UI models from the shared store without making API calls
    func refreshFromStore() {
        boards = store.boards.map { apiBoard in
            KanbanBoard(
                name: apiBoard.name,
                icon: "folder",
                taskCount: 0,
                boardId: apiBoard.boardId
            )
        }
        tasks = store.tasks.map { apiTask in
            KanbanTask(
                title: apiTask.title,
                description: apiTask.description ?? "",
                status: TaskStatus(apiString: apiTask.status ?? "todo"),
                priority: TaskPriority(apiString: apiTask.priority ?? "medium"),
                assignee: apiTask.assigneeId ?? "Unassigned",
                dueDate: apiTask.dueDate ?? "",
                labels: apiTask.tags,
                taskId: apiTask.taskId,
                boardId: apiTask.boardId,
                columnId: apiTask.columnId
            )
        }
    }
}
