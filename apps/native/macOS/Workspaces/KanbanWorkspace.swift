//
//  KanbanWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Kanban task management workspace with three-pane Outlook-style layout.
//

import SwiftUI

struct KanbanWorkspace: View {
    @State private var boards: [KanbanBoard] = KanbanBoard.mockBoards
    @State private var tasks: [KanbanTask] = KanbanTask.mockTasks
    @State private var selectedBoard: KanbanBoard? = nil
    @State private var selectedTask: KanbanTask? = nil
    @State private var showNewBoardSheet = false
    @State private var showNewTaskSheet = false
    @State private var boardToDelete: KanbanBoard? = nil
    @State private var taskToDelete: KanbanTask? = nil
    @State private var newBoardName = ""
    @State private var newTaskTitle = ""

    var body: some View {
        ThreePaneLayout {
            // Left Pane: Boards
            boardListPane
        } middlePane: {
            // Middle Pane: Task List
            taskListPane
        } rightPane: {
            // Right Pane: Task Detail
            taskDetailPane
        }
        .sheet(isPresented: $showNewBoardSheet) {
            NewBoardSheet(boardName: $newBoardName, onSave: {
                createBoard()
            })
        }
        .sheet(isPresented: $showNewTaskSheet) {
            NewTaskSheet(taskTitle: $newTaskTitle, onSave: {
                createTask()
            })
        }
        .alert("Delete Board", isPresented: .constant(boardToDelete != nil), presenting: boardToDelete) { board in
            Button("Cancel", role: .cancel) {
                boardToDelete = nil
            }
            Button("Delete", role: .destructive) {
                deleteBoard(board)
            }
        } message: { board in
            Text("Are you sure you want to delete '\(board.name)'? This will remove all associated tasks.")
        }
        .alert("Delete Task", isPresented: .constant(taskToDelete != nil), presenting: taskToDelete) { task in
            Button("Cancel", role: .cancel) {
                taskToDelete = nil
            }
            Button("Delete", role: .destructive) {
                deleteTask(task)
            }
        } message: { task in
            Text("Are you sure you want to delete '\(task.title)'?")
        }
    }

    // MARK: - Left Pane: Boards

    private var boardListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Boards",
                icon: "square.grid.2x2",
                action: {
                    newBoardName = ""
                    showNewBoardSheet = true
                },
                actionIcon: "plus.circle.fill"
            )

            Divider()

            List(boards, selection: $selectedBoard) { board in
                BoardRow(
                    board: board,
                    onDelete: {
                        boardToDelete = board
                    }
                )
                .tag(board)
            }
            .listStyle(.sidebar)
        }
    }

    // MARK: - Middle Pane: Tasks

    private var taskListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: selectedBoard?.name ?? "Tasks",
                subtitle: selectedBoard != nil ? "\(tasks.count) tasks" : nil,
                action: {
                    guard selectedBoard != nil else { return }
                    newTaskTitle = ""
                    showNewTaskSheet = true
                },
                actionIcon: "plus.circle.fill"
            )

            Divider()

            if selectedBoard == nil {
                PaneEmptyState(
                    icon: "square.grid.2x2",
                    title: "No board selected",
                    subtitle: "Select a board to view tasks"
                )
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(tasks) { task in
                            TaskRow(
                                task: task,
                                isSelected: selectedTask?.id == task.id,
                                onDelete: {
                                    taskToDelete = task
                                }
                            )
                            .onTapGesture {
                                selectedTask = task
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Right Pane: Task Detail

    private var taskDetailPane: some View {
        Group {
            if let task = selectedTask {
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
                            taskToDelete = task
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

    // MARK: - CRUD Operations

    private func createBoard() {
        guard !newBoardName.isEmpty else { return }

        let newBoard = KanbanBoard(
            name: newBoardName,
            icon: "folder",
            taskCount: 0
        )

        withAnimation {
            boards.append(newBoard)
        }

        showNewBoardSheet = false
        newBoardName = ""
    }

    private func deleteBoard(_ board: KanbanBoard) {
        withAnimation {
            boards.removeAll { $0.id == board.id }

            // Clear selection if deleted board was selected
            if selectedBoard?.id == board.id {
                selectedBoard = nil
                selectedTask = nil
            }
        }

        boardToDelete = nil
    }

    private func createTask() {
        guard !newTaskTitle.isEmpty else { return }

        let newTask = KanbanTask(
            title: newTaskTitle,
            description: "New task description",
            status: .todo,
            priority: .medium,
            assignee: "Unassigned",
            dueDate: "TBD",
            labels: []
        )

        withAnimation {
            tasks.append(newTask)
        }

        showNewTaskSheet = false
        newTaskTitle = ""
    }

    private func deleteTask(_ task: KanbanTask) {
        withAnimation {
            tasks.removeAll { $0.id == task.id }

            // Clear selection if deleted task was selected
            if selectedTask?.id == task.id {
                selectedTask = nil
            }
        }

        taskToDelete = nil
    }
}

// MARK: - Supporting Views

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

// MARK: - Models

struct KanbanBoard: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let icon: String
    let taskCount: Int

    static let mockBoards = [
        KanbanBoard(name: "Product Roadmap", icon: "map", taskCount: 24),
        KanbanBoard(name: "Sprint 12", icon: "bolt", taskCount: 18),
        KanbanBoard(name: "Bug Fixes", icon: "ant", taskCount: 12),
        KanbanBoard(name: "Research", icon: "magnifyingglass", taskCount: 8)
    ]
}

struct KanbanTask: Identifiable {
    let id = UUID()
    let title: String
    let description: String
    let status: TaskStatus
    let priority: TaskPriority
    let assignee: String
    let dueDate: String
    let labels: [String]

    static let mockTasks = [
        KanbanTask(title: "Implement model tag system", description: "Add capability tags to models for better organization", status: .inProgress, priority: .high, assignee: "Alice Johnson", dueDate: "Nov 30, 2025", labels: ["Feature", "Backend"]),
        KanbanTask(title: "Design Liquid Glass UI", description: "Create macOS Tahoe-inspired UI components", status: .inProgress, priority: .high, assignee: "Bob Smith", dueDate: "Nov 28, 2025", labels: ["Design", "UI"]),
        KanbanTask(title: "Fix chat streaming bug", description: "Messages not displaying correctly during streaming", status: .todo, priority: .medium, assignee: "Carol Davis", dueDate: "Dec 2, 2025", labels: ["Bug", "Chat"]),
        KanbanTask(title: "Add model performance metrics", description: "Track inference time and token usage", status: .todo, priority: .low, assignee: "David Wilson", dueDate: "Dec 5, 2025", labels: ["Analytics"]),
        KanbanTask(title: "Write API documentation", description: "Document all REST endpoints", status: .done, priority: .medium, assignee: "Eve Martinez", dueDate: "Nov 20, 2025", labels: ["Documentation"])
    ]
}

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
}

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
}

// MARK: - New Board/Task Sheets

struct NewBoardSheet: View {
    @Binding var boardName: String
    let onSave: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 24) {
            // Header
            HStack {
                Text("New Board")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color(nsColor: .controlBackgroundColor))
                        )
                }
                .buttonStyle(.plain)
                .help("Close (Esc)")
                .keyboardShortcut(.cancelAction)
            }

            Divider()

            // Form
            VStack(alignment: .leading, spacing: 12) {
                Text("Board Name")
                    .font(.headline)

                TextField("Enter board name", text: $boardName)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        onSave()
                        dismiss()
                    }
            }

            Spacer()

            // Footer buttons
            HStack {
                Spacer()

                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Button("Create") {
                    onSave()
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
                .disabled(boardName.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 400, height: 250)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

struct NewTaskSheet: View {
    @Binding var taskTitle: String
    let onSave: () -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 24) {
            // Header
            HStack {
                Text("New Task")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color(nsColor: .controlBackgroundColor))
                        )
                }
                .buttonStyle(.plain)
                .help("Close (Esc)")
                .keyboardShortcut(.cancelAction)
            }

            Divider()

            // Form
            VStack(alignment: .leading, spacing: 12) {
                Text("Task Title")
                    .font(.headline)

                TextField("Enter task title", text: $taskTitle)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        onSave()
                        dismiss()
                    }
            }

            Spacer()

            // Footer buttons
            HStack {
                Spacer()

                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Button("Create") {
                    onSave()
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
                .disabled(taskTitle.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 400, height: 250)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

#Preview {
    KanbanWorkspace()
}
