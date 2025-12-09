//
//  KanbanWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Kanban task management workspace with three-pane Outlook-style layout.
//

import SwiftUI

struct KanbanWorkspace: View {
    @State private var boards: [KanbanBoard] = []
    @State private var tasks: [KanbanTask] = []
    @State private var selectedBoard: KanbanBoard? = nil
    @State private var selectedTask: KanbanTask? = nil
    @State private var showNewBoardSheet = false
    @State private var showNewTaskSheet = false
    @State private var boardToDelete: KanbanBoard? = nil
    @State private var taskToDelete: KanbanTask? = nil
    @State private var newBoardName = ""
    @State private var newTaskTitle = ""
    @State private var isLoading = false

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
        .onAppear {
            loadBoardsAndTasks()
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

    // MARK: - Data Loading

    private func loadBoardsAndTasks() {
        isLoading = true

        Task {
            do {
                // Note: Kanban backend requires a project_id
                // Using a default project for now - in production this should be user-selected
                let defaultProjectId = "default"

                // Try to load boards from API
                let apiBoards = try await KanbanService.shared.listBoards(projectId: defaultProjectId)

                await MainActor.run {
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
                        selectedBoard = boards.first
                        Task {
                            await loadTasks(boardId: firstBoard.boardId)
                        }
                    }

                    isLoading = false
                }
            } catch {
                // Show empty state if API fails
                print("Kanban API error: \(error.localizedDescription)")
                await MainActor.run {
                    boards = []
                    tasks = []
                    isLoading = false
                }
            }
        }
    }

    private func loadTasks(boardId: String) async {
        do {
            let apiTasks = try await KanbanService.shared.listTasks(boardId: boardId)

            await MainActor.run {
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
            }
        } catch {
            print("Failed to load tasks: \(error.localizedDescription)")
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

    // MARK: - CRUD Operations

    private func createBoard() {
        guard !newBoardName.isEmpty else { return }

        Task {
            do {
                // Create board via API
                let defaultProjectId = "default"
                let apiBoard = try await KanbanService.shared.createBoard(
                    projectId: defaultProjectId,
                    name: newBoardName
                )

                await MainActor.run {
                    let newBoard = KanbanBoard(
                        name: apiBoard.name,
                        icon: "folder",
                        taskCount: 0,
                        boardId: apiBoard.boardId
                    )

                    withAnimation {
                        boards.append(newBoard)
                        selectedBoard = newBoard
                    }

                    showNewBoardSheet = false
                    newBoardName = ""
                }
            } catch {
                print("Failed to create board: \(error.localizedDescription)")
                // Fall back to local-only creation
                await MainActor.run {
                    let newBoard = KanbanBoard(
                        name: newBoardName,
                        icon: "folder",
                        taskCount: 0,
                        boardId: nil
                    )

                    withAnimation {
                        boards.append(newBoard)
                    }

                    showNewBoardSheet = false
                    newBoardName = ""
                }
            }
        }
    }

    private func deleteBoard(_ board: KanbanBoard) {
        Task {
            do {
                // Delete from API if we have a backend ID
                if let boardId = board.boardId {
                    try await KanbanService.shared.deleteBoard(boardId: boardId)
                }

                await MainActor.run {
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
            } catch {
                print("Failed to delete board from API: \(error.localizedDescription)")
                // Still remove locally even if API fails
                await MainActor.run {
                    withAnimation {
                        boards.removeAll { $0.id == board.id }

                        if selectedBoard?.id == board.id {
                            selectedBoard = nil
                            selectedTask = nil
                        }
                    }

                    boardToDelete = nil
                }
            }
        }
    }

    private func createTask() {
        guard !newTaskTitle.isEmpty else { return }
        guard let currentBoard = selectedBoard, let boardId = currentBoard.boardId else {
            print("Cannot create task: no board selected or board has no backend ID")
            showNewTaskSheet = false
            newTaskTitle = ""
            return
        }

        Task {
            do {
                // For now, use "todo" as the default column_id
                // In a full implementation, we'd fetch columns and use the first one
                let defaultColumnId = "todo"

                let apiTask = try await KanbanService.shared.createTask(
                    boardId: boardId,
                    columnId: defaultColumnId,
                    title: newTaskTitle,
                    description: "New task description",
                    status: "todo",
                    priority: "medium"
                )

                await MainActor.run {
                    let newTask = KanbanTask(
                        title: apiTask.title,
                        description: apiTask.description ?? "",
                        status: taskStatusFromString(apiTask.status ?? "todo"),
                        priority: taskPriorityFromString(apiTask.priority ?? "medium"),
                        assignee: apiTask.assigneeId ?? "Unassigned",
                        dueDate: apiTask.dueDate ?? "TBD",
                        labels: apiTask.tags,
                        taskId: apiTask.taskId,
                        boardId: apiTask.boardId,
                        columnId: apiTask.columnId
                    )

                    withAnimation {
                        tasks.append(newTask)
                    }

                    showNewTaskSheet = false
                    newTaskTitle = ""
                }
            } catch {
                print("Failed to create task: \(error.localizedDescription)")
                // Fall back to local-only creation
                await MainActor.run {
                    let newTask = KanbanTask(
                        title: newTaskTitle,
                        description: "New task description",
                        status: .todo,
                        priority: .medium,
                        assignee: "Unassigned",
                        dueDate: "TBD",
                        labels: [],
                        taskId: nil,
                        boardId: nil,
                        columnId: nil
                    )

                    withAnimation {
                        tasks.append(newTask)
                    }

                    showNewTaskSheet = false
                    newTaskTitle = ""
                }
            }
        }
    }

    private func deleteTask(_ task: KanbanTask) {
        Task {
            do {
                // Delete from API if we have a backend ID
                if let taskId = task.taskId {
                    try await KanbanService.shared.deleteTask(taskId: taskId)
                }

                await MainActor.run {
                    withAnimation {
                        tasks.removeAll { $0.id == task.id }

                        // Clear selection if deleted task was selected
                        if selectedTask?.id == task.id {
                            selectedTask = nil
                        }
                    }

                    taskToDelete = nil
                }
            } catch {
                print("Failed to delete task from API: \(error.localizedDescription)")
                // Still remove locally even if API fails
                await MainActor.run {
                    withAnimation {
                        tasks.removeAll { $0.id == task.id }

                        if selectedTask?.id == task.id {
                            selectedTask = nil
                        }
                    }

                    taskToDelete = nil
                }
            }
        }
    }
}

#Preview {
    KanbanWorkspace()
}
