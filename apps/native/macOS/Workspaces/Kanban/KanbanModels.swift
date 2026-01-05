//
//  KanbanModels.swift
//  MagnetarStudio (macOS)
//
//  Kanban board and task models - Extracted from KanbanWorkspace.swift
//

import SwiftUI

// MARK: - Board Model

struct KanbanBoard: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let icon: String
    let taskCount: Int
    let boardId: String?  // Backend board ID for API operations

    static let mockBoards = [
        KanbanBoard(name: "Product Roadmap", icon: "map", taskCount: 24, boardId: nil),
        KanbanBoard(name: "Sprint 12", icon: "bolt", taskCount: 18, boardId: nil),
        KanbanBoard(name: "Bug Fixes", icon: "ant", taskCount: 12, boardId: nil),
        KanbanBoard(name: "Research", icon: "magnifyingglass", taskCount: 8, boardId: nil)
    ]
}

// MARK: - Task Model

struct KanbanTask: Identifiable {
    let id = UUID()
    let title: String
    let description: String
    let status: TaskStatus
    let priority: TaskPriority
    let assignee: String
    let dueDate: String
    let labels: [String]
    let taskId: String?  // Backend task ID for API operations
    let boardId: String?  // Backend board ID
    let columnId: String?  // Backend column ID

    static let mockTasks = [
        KanbanTask(title: "Implement model tag system", description: "Add capability tags to models for better organization", status: .inProgress, priority: .high, assignee: "Alice Johnson", dueDate: "Nov 30, 2025", labels: ["Feature", "Backend"], taskId: nil, boardId: nil, columnId: nil),
        KanbanTask(title: "Design Liquid Glass UI", description: "Create macOS Tahoe-inspired UI components", status: .inProgress, priority: .high, assignee: "Bob Smith", dueDate: "Nov 28, 2025", labels: ["Design", "UI"], taskId: nil, boardId: nil, columnId: nil),
        KanbanTask(title: "Fix chat streaming bug", description: "Messages not displaying correctly during streaming", status: .todo, priority: .medium, assignee: "Carol Davis", dueDate: "Dec 2, 2025", labels: ["Bug", "Chat"], taskId: nil, boardId: nil, columnId: nil),
        KanbanTask(title: "Add model performance metrics", description: "Track inference time and token usage", status: .todo, priority: .low, assignee: "David Wilson", dueDate: "Dec 5, 2025", labels: ["Analytics"], taskId: nil, boardId: nil, columnId: nil),
        KanbanTask(title: "Write API documentation", description: "Document all REST endpoints", status: .done, priority: .medium, assignee: "Eve Martinez", dueDate: "Nov 20, 2025", labels: ["Documentation"], taskId: nil, boardId: nil, columnId: nil)
    ]
}

// MARK: - Task Status

enum TaskStatus: String {
    case todo = "To Do"
    case inProgress = "In Progress"
    case done = "Done"

    var color: Color {
        switch self {
        case .todo: return .gray
        case .inProgress: return .blue
        case .done: return .green
        }
    }

    /// Parse status from backend API string
    init(apiString: String) {
        switch apiString.lowercased() {
        case "done": self = .done
        case "in_progress", "inprogress": self = .inProgress
        default: self = .todo
        }
    }
}

// MARK: - Task Priority

enum TaskPriority: String {
    case low = "Low"
    case medium = "Medium"
    case high = "High"

    var color: Color {
        switch self {
        case .low: return .gray
        case .medium: return .orange
        case .high: return .red
        }
    }

    /// Parse priority from backend API string
    init(apiString: String) {
        switch apiString.lowercased() {
        case "high": self = .high
        case "low": self = .low
        default: self = .medium
        }
    }
}
