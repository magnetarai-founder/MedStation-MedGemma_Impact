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
                        .foregroundColor(.secondary)
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
                        .foregroundColor(.secondary)
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
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "checkmark.circle")
                .font(.title3)
                .foregroundStyle(task.status.color)

            VStack(alignment: .leading, spacing: 4) {
                Text(task.title)
                    .font(.headline)
                    .foregroundColor(.textPrimary)

                HStack(spacing: 8) {
                    StatusBadge(status: task.status)
                    PriorityBadge(priority: task.priority)
                }
            }

            Spacer()

            if isHovered {
                Button {
                    onDelete()
                } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
                .help("Delete Task")
            }
        }
        .padding(12)
        .background(isSelected ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
        .cornerRadius(8)
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
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
            .foregroundColor(status.color)
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
            .foregroundColor(priority.color)
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
                .foregroundColor(.secondary)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Text(value)
                    .font(.body)
            }
        }
    }
}
