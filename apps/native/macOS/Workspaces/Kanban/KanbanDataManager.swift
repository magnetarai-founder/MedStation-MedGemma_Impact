//
//  KanbanDataManager.swift
//  MagnetarStudio (macOS)
//
//  Data loading manager - Extracted from KanbanWorkspace.swift (Phase 6.20)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "KanbanDataManager")

@MainActor
@Observable
class KanbanDataManager {
    var boards: [KanbanBoard] = []
    var tasks: [KanbanTask] = []
    var isLoading: Bool = false

    private let defaultProjectId = "default"

    func loadBoardsAndTasks() async -> KanbanBoard? {
        isLoading = true

        do {
            // Try to load boards from API
            let apiBoards = try await KanbanService.shared.listBoards(projectId: defaultProjectId)

            // Convert API boards to UI models
            boards = apiBoards.map { apiBoard in
                KanbanBoard(
                    name: apiBoard.name,
                    icon: "folder",
                    taskCount: 0,  // Would need separate API call to get count
                    boardId: apiBoard.boardId
                )
            }

            // If we have boards, load tasks for the first one
            if let firstBoard = apiBoards.first {
                await loadTasks(boardId: firstBoard.boardId)
                isLoading = false
                return boards.first
            }

            isLoading = false
            return nil
        } catch {
            // Show empty state if API fails
            logger.error("Kanban API error: \(error.localizedDescription)")
            boards = []
            tasks = []
            isLoading = false
            return nil
        }
    }

    func loadTasks(boardId: String) async {
        do {
            let apiTasks = try await KanbanService.shared.listTasks(boardId: boardId)

            tasks = apiTasks.map { apiTask in
                KanbanTask(
                    title: apiTask.title,
                    description: apiTask.description ?? "",
                    status: taskStatusFromString(apiTask.status ?? "todo"),
                    priority: taskPriorityFromString(apiTask.priority ?? "medium"),
                    assignee: apiTask.assigneeId ?? "Unassigned",
                    dueDate: apiTask.dueDate ?? "",
                    labels: apiTask.tags,
                    taskId: apiTask.taskId,
                    boardId: apiTask.boardId,
                    columnId: apiTask.columnId
                )
            }
        } catch {
            logger.error("Failed to load tasks: \(error.localizedDescription)")
        }
    }

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
