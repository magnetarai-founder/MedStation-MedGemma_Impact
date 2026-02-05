//
//  KanbanTaskDetailPane.swift
//  MagnetarStudio (macOS)
//
//  Task detail pane view - Extracted from KanbanWorkspace.swift (Phase 6.20)
//  Enhanced with quick toggles and urgency indicators
//

import SwiftUI

struct KanbanTaskDetailPane: View {
    let task: KanbanTask?
    let onDelete: () -> Void
    var onStatusChange: ((TaskStatus) -> Void)? = nil
    var onPriorityChange: ((TaskPriority) -> Void)? = nil

    @State private var isHoveredStatus = false
    @State private var isHoveredPriority = false
    @State private var showCopied = false
    @State private var copyResetTask: Task<Void, Never>?

    var body: some View {
        Group {
            if let task = task {
                VStack(spacing: 0) {
                    // Task header
                    taskHeader(task: task)

                    Divider()

                    // Task details
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            // Quick Actions Bar
                            quickActionsBar(task: task)

                            // Due Date with Urgency
                            dueDateSection(task: task)

                            Divider()

                            // Description
                            descriptionSection(task: task)

                            Divider()

                            // Metadata
                            metadataSection(task: task)

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

    // MARK: - Header

    private func taskHeader(task: KanbanTask) -> some View {
        HStack(spacing: 12) {
            // Status icon - clickable to cycle
            Button {
                onStatusChange?(task.status.next())
            } label: {
                Image(systemName: task.status.icon)
                    .font(.title)
                    .foregroundStyle(task.status.color)
                    .contentTransition(.symbolEffect(.replace))
            }
            .buttonStyle(.plain)
            .help("Click to change status")

            VStack(alignment: .leading, spacing: 4) {
                Text(task.title)
                    .font(.title2)
                    .fontWeight(.bold)

                HStack(spacing: 8) {
                    // Clickable status badge
                    InteractiveStatusBadge(
                        status: task.status,
                        onTap: { onStatusChange?(task.status.next()) }
                    )

                    // Clickable priority badge
                    InteractivePriorityBadge(
                        priority: task.priority,
                        onTap: { onPriorityChange?(task.priority.next()) }
                    )
                }
            }

            Spacer()

            // Action buttons
            HStack(spacing: 8) {
                // Copy task title
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(task.title, forType: .string)
                    showCopied = true
                    copyResetTask?.cancel()
                    copyResetTask = Task {
                        try? await Task.sleep(for: .seconds(1.5))
                        guard !Task.isCancelled else { return }
                        showCopied = false
                    }
                } label: {
                    Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 14))
                        .foregroundColor(showCopied ? .green : .secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color(nsColor: .controlBackgroundColor))
                        )
                }
                .buttonStyle(.plain)
                .help(showCopied ? "Copied!" : "Copy task title")

                // Delete button
                Button {
                    onDelete()
                } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 14))
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
        }
        .padding(24)
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Quick Actions

    private func quickActionsBar(task: KanbanTask) -> some View {
        HStack(spacing: 12) {
            // Status quick select
            ForEach(TaskStatus.allCases, id: \.self) { status in
                Button {
                    onStatusChange?(status)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: status.icon)
                            .font(.system(size: 12))
                        Text(status.rawValue)
                            .font(.caption)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(task.status == status ? status.color.opacity(0.2) : Color.gray.opacity(0.1))
                    .foregroundColor(task.status == status ? status.color : .secondary)
                    .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }

            Spacer()

            // Priority quick select
            ForEach(TaskPriority.allCases, id: \.self) { priority in
                Button {
                    onPriorityChange?(priority)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: priority.icon)
                            .font(.system(size: 10))
                        Text(priority.rawValue)
                            .font(.caption)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(task.priority == priority ? priority.color.opacity(0.2) : Color.gray.opacity(0.1))
                    .foregroundColor(task.priority == priority ? priority.color : .secondary)
                    .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Due Date Section

    private func dueDateSection(task: KanbanTask) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Due Date")
                .font(.headline)

            HStack(spacing: 12) {
                Image(systemName: task.dueDateUrgency.icon)
                    .font(.title2)
                    .foregroundColor(task.dueDateUrgency.color)

                VStack(alignment: .leading, spacing: 2) {
                    Text(task.relativeDueDate)
                        .font(.body)
                        .fontWeight(.medium)
                        .foregroundColor(task.dueDateUrgency.color)

                    if task.dueDateParsed != nil && task.dueDateUrgency != .noDueDate {
                        Text(task.dueDate)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                // Urgency indicator
                if task.dueDateUrgency == .overdue {
                    Text("OVERDUE")
                        .font(.caption2)
                        .fontWeight(.bold)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.red.opacity(0.2))
                        .foregroundColor(.red)
                        .clipShape(Capsule())
                } else if task.dueDateUrgency == .dueToday {
                    Text("TODAY")
                        .font(.caption2)
                        .fontWeight(.bold)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.orange.opacity(0.2))
                        .foregroundColor(.orange)
                        .clipShape(Capsule())
                }
            }
            .padding(12)
            .background(task.dueDateUrgency.color.opacity(0.05))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    // MARK: - Description

    private func descriptionSection(task: KanbanTask) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Description")
                .font(.headline)

            Text(task.description)
                .font(.body)
                .foregroundColor(.secondary)
                .textSelection(.enabled)
        }
    }

    // MARK: - Metadata

    private func metadataSection(task: KanbanTask) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            DetailRow(icon: "person", label: "Assignee", value: task.assignee)

            // Labels with colored chips
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "tag")
                    .foregroundColor(.secondary)
                    .frame(width: 20)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Labels")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if task.labels.isEmpty {
                        Text("No labels")
                            .font(.body)
                            .foregroundColor(.textTertiary)
                    } else {
                        FlowLayout(spacing: 6) {
                            ForEach(task.labels, id: \.self) { label in
                                Text(label)
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(labelColor(for: label).opacity(0.15))
                                    .foregroundColor(labelColor(for: label))
                                    .clipShape(Capsule())
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Helpers

    private func labelColor(for label: String) -> Color {
        // Consistent colors based on label name
        let colors: [Color] = [.blue, .purple, .pink, .orange, .teal, .indigo]
        let hash = abs(label.hashValue)
        return colors[hash % colors.count]
    }
}

// MARK: - Interactive Status Badge

struct InteractiveStatusBadge: View {
    let status: TaskStatus
    let onTap: () -> Void
    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Image(systemName: status.icon)
                    .font(.system(size: 10))
                Text(status.rawValue)
                    .font(.caption2)
                    .fontWeight(.semibold)
                if isHovered {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 8))
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(status.color.opacity(isHovered ? 0.3 : 0.2))
            .foregroundColor(status.color)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .help("Click to cycle status")
    }
}

// MARK: - Interactive Priority Badge

struct InteractivePriorityBadge: View {
    let priority: TaskPriority
    let onTap: () -> Void
    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 4) {
                Image(systemName: priority.icon)
                    .font(.system(size: 10))
                Text(priority.rawValue)
                    .font(.caption2)
                    .fontWeight(.semibold)
                if isHovered {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 8))
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(priority.color.opacity(isHovered ? 0.3 : 0.2))
            .foregroundColor(priority.color)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .help("Click to cycle priority")
    }
}

// Note: FlowLayout is defined in Shared/Views/ModelTagEditorSheet.swift
