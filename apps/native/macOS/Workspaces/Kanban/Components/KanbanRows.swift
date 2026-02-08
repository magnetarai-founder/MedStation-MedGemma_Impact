//
//  KanbanRows.swift
//  MagnetarStudio (macOS)
//
//  Kanban row and badge components - Extracted from KanbanWorkspace.swift
//

import SwiftUI

// MARK: - Board Row

struct BoardRow: View {
    let board: KanbanBoard
    let onDelete: () -> Void
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Label {
                VStack(alignment: .leading, spacing: 2) {
                    Text(board.name)
                        .font(.headline)
                    Text("\(board.taskCount) tasks")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            } icon: {
                Image(systemName: board.icon)
                    .foregroundStyle(LinearGradient.magnetarGradient)
            }

            Spacer()

            if isHovered {
                Button {
                    onDelete()
                } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 14))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("Delete Board")
            }
        }
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Task Row

struct TaskRow: View {
    let task: KanbanTask
    let isSelected: Bool
    let onDelete: () -> Void
    var onStatusChange: ((TaskStatus) -> Void)? = nil
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Status icon - clickable
            Button {
                onStatusChange?(task.status.next())
            } label: {
                Image(systemName: task.status.icon)
                    .font(.title3)
                    .foregroundStyle(task.status.color)
                    .contentTransition(.symbolEffect(.replace))
            }
            .buttonStyle(.plain)
            .help("Click to change status")

            VStack(alignment: .leading, spacing: 4) {
                Text(task.title)
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                HStack(spacing: 8) {
                    StatusBadge(status: task.status)
                    PriorityBadge(priority: task.priority)

                    // Due date indicator
                    DueDateIndicator(task: task)
                }
            }

            Spacer()

            // Hover actions
            if isHovered {
                HStack(spacing: 4) {
                    // Quick complete toggle
                    Button {
                        if task.status != .done {
                            onStatusChange?(.done)
                        } else {
                            onStatusChange?(.todo)
                        }
                    } label: {
                        Image(systemName: task.status == .done ? "arrow.uturn.backward" : "checkmark")
                            .font(.system(size: 12))
                            .foregroundStyle(task.status == .done ? .orange : .green)
                            .frame(width: 24, height: 24)
                            .background(
                                Circle()
                                    .fill(Color(nsColor: .controlBackgroundColor))
                            )
                    }
                    .buttonStyle(.plain)
                    .help(task.status == .done ? "Mark as To Do" : "Mark as Done")

                    // Delete
                    Button {
                        onDelete()
                    } label: {
                        Image(systemName: "trash")
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                            .frame(width: 24, height: 24)
                            .background(
                                Circle()
                                    .fill(Color(nsColor: .controlBackgroundColor))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Delete Task")
                }
                .transition(.opacity.combined(with: .scale(scale: 0.9)))
            }
        }
        .padding(12)
        .background(isSelected ? Color.magnetarPrimary.opacity(0.1) : (isHovered ? Color.gray.opacity(0.05) : Color.clear))
        .cornerRadius(8)
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Due Date Indicator

struct DueDateIndicator: View {
    let task: KanbanTask

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: task.dueDateUrgency.icon)
                .font(.system(size: 10))
            Text(compactDueDate)
                .font(.caption2)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .background(task.dueDateUrgency.color.opacity(0.15))
        .foregroundStyle(task.dueDateUrgency.color)
        .clipShape(Capsule())
    }

    private var compactDueDate: String {
        guard let date = task.dueDateParsed else { return task.dueDate }

        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let dueDay = calendar.startOfDay(for: date)
        let days = calendar.dateComponents([.day], from: today, to: dueDay).day ?? 0

        switch days {
        case ..<0:
            return "\(abs(days))d late"
        case 0:
            return "Today"
        case 1:
            return "Tomorrow"
        case 2...7:
            return "in \(days)d"
        default:
            let formatter = DateFormatter()
            formatter.dateFormat = "MMM d"
            return formatter.string(from: date)
        }
    }
}

// MARK: - Status Badge

struct StatusBadge: View {
    let status: TaskStatus

    var body: some View {
        Text(status.rawValue)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(status.color.opacity(0.2))
            .foregroundStyle(status.color)
            .cornerRadius(6)
    }
}

// MARK: - Priority Badge

struct PriorityBadge: View {
    let priority: TaskPriority

    var body: some View {
        Text(priority.rawValue)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(priority.color.opacity(0.2))
            .foregroundStyle(priority.color)
            .cornerRadius(6)
    }
}

// MARK: - Detail Row

struct DetailRow: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(.secondary)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Text(value)
                    .font(.body)
            }
        }
    }
}
