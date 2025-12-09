//
//  KanbanTaskDetailPane.swift
//  MagnetarStudio (macOS)
//
//  Task detail pane view - Extracted from KanbanWorkspace.swift (Phase 6.20)
//

import SwiftUI

struct KanbanTaskDetailPane: View {
    let task: KanbanTask?
    let onDelete: () -> Void

    var body: some View {
        Group {
            if let task = task {
                VStack(spacing: 0) {
                    // Task header
                    HStack(spacing: 12) {
                        Image(systemName: "checkmark.circle")
                            .font(.title)
                            .foregroundStyle(task.status.color)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(task.title)
                                .font(.title2)
                                .fontWeight(.bold)

                            HStack(spacing: 8) {
                                StatusBadge(status: task.status)
                                PriorityBadge(priority: task.priority)
                            }
                        }

                        Spacer()

                        // Delete button
                        Button {
                            onDelete()
                        } label: {
                            Image(systemName: "trash")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                                .frame(width: 28, height: 28)
                                .background(
                                    Circle()
                                        .fill(Color(nsColor: .controlBackgroundColor))
                                )
                        }
                        .buttonStyle(.plain)
                        .help("Delete Task")
                    }
                    .padding(24)
                    .background(Color.surfaceTertiary.opacity(0.3))

                    Divider()

                    // Task details
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            // Description
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Description")
                                    .font(.headline)

                                Text(task.description)
                                    .font(.body)
                                    .foregroundColor(.secondary)
                            }

                            Divider()

                            // Metadata
                            VStack(alignment: .leading, spacing: 12) {
                                DetailRow(icon: "person", label: "Assignee", value: task.assignee)
                                DetailRow(icon: "calendar", label: "Due Date", value: task.dueDate)
                                DetailRow(icon: "tag", label: "Labels", value: task.labels.joined(separator: ", "))
                            }

                            Spacer()
                        }
                        .padding(24)
                    }
                }
            } else {
                PaneEmptyState(
                    icon: "checkmark.circle",
                    title: "No task selected",
                    subtitle: "Select a task to view details"
                )
            }
        }
    }
}
