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

enum TaskStatus: String, CaseIterable {
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

    var icon: String {
        switch self {
        case .todo: return "circle"
        case .inProgress: return "circle.lefthalf.filled"
        case .done: return "checkmark.circle.fill"
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

    /// Get the next status in cycle
    func next() -> TaskStatus {
        switch self {
        case .todo: return .inProgress
        case .inProgress: return .done
        case .done: return .todo
        }
    }
}

// MARK: - Task Priority

enum TaskPriority: String, CaseIterable {
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

    var icon: String {
        switch self {
        case .low: return "arrow.down"
        case .medium: return "equal"
        case .high: return "arrow.up"
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

    /// Get the next priority in cycle
    func next() -> TaskPriority {
        switch self {
        case .low: return .medium
        case .medium: return .high
        case .high: return .low
        }
    }
}

// MARK: - Due Date Utilities

enum DueDateUrgency {
    case overdue
    case dueToday
    case dueSoon  // Within 3 days
    case upcoming
    case noDueDate

    var color: Color {
        switch self {
        case .overdue: return .red
        case .dueToday: return .orange
        case .dueSoon: return .yellow
        case .upcoming: return .secondary
        case .noDueDate: return .secondary
        }
    }

    var icon: String {
        switch self {
        case .overdue: return "exclamationmark.circle.fill"
        case .dueToday: return "clock.fill"
        case .dueSoon: return "calendar.badge.clock"
        case .upcoming: return "calendar"
        case .noDueDate: return "calendar"
        }
    }
}

extension KanbanTask {
    /// Parse the due date string to a Date object
    var dueDateParsed: Date? {
        let formatters: [DateFormatter] = {
            let isoFormatter = DateFormatter()
            isoFormatter.dateFormat = "yyyy-MM-dd"

            let shortFormatter = DateFormatter()
            shortFormatter.dateFormat = "MMM d, yyyy"

            let mediumFormatter = DateFormatter()
            mediumFormatter.dateStyle = .medium

            return [isoFormatter, shortFormatter, mediumFormatter]
        }()

        for formatter in formatters {
            if let date = formatter.date(from: dueDate) {
                return date
            }
        }
        return nil
    }

    /// Calculate the urgency level based on due date
    var dueDateUrgency: DueDateUrgency {
        guard let date = dueDateParsed else { return .noDueDate }

        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let dueDay = calendar.startOfDay(for: date)
        let days = calendar.dateComponents([.day], from: today, to: dueDay).day ?? 0

        if days < 0 {
            return .overdue
        } else if days == 0 {
            return .dueToday
        } else if days <= 3 {
            return .dueSoon
        } else {
            return .upcoming
        }
    }

    /// Get a relative string for the due date
    var relativeDueDate: String {
        guard let date = dueDateParsed else { return dueDate }

        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let dueDay = calendar.startOfDay(for: date)
        let days = calendar.dateComponents([.day], from: today, to: dueDay).day ?? 0

        switch days {
        case ..<(-1):
            return "\(abs(days)) days overdue"
        case -1:
            return "1 day overdue"
        case 0:
            return "Due today"
        case 1:
            return "Due tomorrow"
        case 2...7:
            return "Due in \(days) days"
        default:
            // For dates further out, show the actual date
            let formatter = DateFormatter()
            formatter.dateStyle = .medium
            return formatter.string(from: date)
        }
    }
}
