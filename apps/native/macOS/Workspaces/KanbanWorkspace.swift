//
//  KanbanWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Kanban task management workspace with three-pane Outlook-style layout.
//  Refactored in Phase 6.20 - extracted detail pane, data manager, and CRUD operations
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "KanbanWorkspace")

struct KanbanWorkspace: View {
    @State private var selectedBoard: KanbanBoard? = nil
    @State private var selectedTask: KanbanTask? = nil
    @State private var showNewBoardSheet = false
    @State private var showNewTaskSheet = false
    @State private var boardToDelete: KanbanBoard? = nil
    @State private var taskToDelete: KanbanTask? = nil
    @State private var newBoardName = ""
    @State private var newTaskTitle = ""
    @State private var dropTargetStatus: TaskStatus?

    // Managers (Phase 6.20)
    @State private var dataManager = KanbanDataManager()
    @State private var crudOperations = KanbanCRUDOperations()

    var body: some View {
        ThreePaneLayout {
            // Left Pane: Boards
            boardListPane
        } middlePane: {
            // Middle Pane: Task List
            taskListPane
        } rightPane: {
            // Right Pane: Task Detail
            KanbanTaskDetailPane(
                task: selectedTask,
                onDelete: {
                    taskToDelete = selectedTask
                },
                onStatusChange: { newStatus in
                    if let task = selectedTask {
                        updateTaskStatus(task, to: newStatus)
                    }
                },
                onPriorityChange: { newPriority in
                    if let task = selectedTask {
                        updateTaskPriority(task, to: newPriority)
                    }
                }
            )
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

            List(dataManager.boards, selection: $selectedBoard) { board in
                BoardRow(
                    board: board,
                    onDelete: {
                        boardToDelete = board
                    }
                )
                .tag(board)
            }
            .listStyle(.sidebar)
            .onChange(of: selectedBoard) { oldValue, newValue in
                if let board = newValue, let boardId = board.boardId {
                    Task {
                        await dataManager.loadTasks(boardId: boardId)
                    }
                }
            }
        }
    }

    // MARK: - Middle Pane: Tasks

    private var taskListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: selectedBoard?.name ?? "Tasks",
                subtitle: selectedBoard != nil ? "\(dataManager.tasks.count) tasks" : nil,
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
                        ForEach(TaskStatus.allCases, id: \.self) { status in
                            let sectionTasks = dataManager.tasks.filter { $0.status == status }

                            statusSectionHeader(status, count: sectionTasks.count)
                                .dropDestination(for: String.self) { items, _ in
                                    handleTaskDrop(items, to: status)
                                    return true
                                } isTargeted: { targeted in
                                    dropTargetStatus = targeted ? status : nil
                                }

                            ForEach(sectionTasks) { task in
                                TaskRow(
                                    task: task,
                                    isSelected: selectedTask?.id == task.id,
                                    onDelete: {
                                        taskToDelete = task
                                    },
                                    onStatusChange: { newStatus in
                                        updateTaskStatus(task, to: newStatus)
                                    }
                                )
                                .draggable(task.id.uuidString)
                                .onTapGesture {
                                    selectedTask = task
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Data Loading

    private func loadBoardsAndTasks() {
        Task {
            let firstBoard = await dataManager.loadBoardsAndTasks()
            selectedBoard = firstBoard
        }
    }

    // MARK: - CRUD Operations

    private func createBoard() {
        Task {
            if let newBoard = await crudOperations.createBoard(name: newBoardName) {
                withAnimation {
                    dataManager.boards.append(newBoard)
                    selectedBoard = newBoard
                }
            }
            showNewBoardSheet = false
            newBoardName = ""
        }
    }

    private func deleteBoard(_ board: KanbanBoard) {
        Task {
            if await crudOperations.deleteBoard(board) {
                withAnimation {
                    dataManager.boards.removeAll { $0.id == board.id }

                    // Clear selection if deleted board was selected
                    if selectedBoard?.id == board.id {
                        selectedBoard = nil
                        selectedTask = nil
                    }
                }
            }
            boardToDelete = nil
        }
    }

    private func createTask() {
        guard let board = selectedBoard else { return }

        Task {
            if let newTask = await crudOperations.createTask(title: newTaskTitle, board: board) {
                withAnimation {
                    dataManager.tasks.append(newTask)
                }
            }
            showNewTaskSheet = false
            newTaskTitle = ""
        }
    }

    private func deleteTask(_ task: KanbanTask) {
        Task {
            if await crudOperations.deleteTask(task) {
                withAnimation {
                    dataManager.tasks.removeAll { $0.id == task.id }

                    // Clear selection if deleted task was selected
                    if selectedTask?.id == task.id {
                        selectedTask = nil
                    }
                }
            }
            taskToDelete = nil
        }
    }

    private func updateTaskStatus(_ task: KanbanTask, to newStatus: TaskStatus) {
        // Update locally for immediate feedback
        withAnimation(.magnetarQuick) {
            if let index = dataManager.tasks.firstIndex(where: { $0.id == task.id }) {
                let updatedTask = KanbanTask(
                    title: task.title,
                    description: task.description,
                    status: newStatus,
                    priority: task.priority,
                    assignee: task.assignee,
                    dueDate: task.dueDate,
                    labels: task.labels,
                    taskId: task.taskId,
                    boardId: task.boardId,
                    columnId: task.columnId
                )
                dataManager.tasks[index] = updatedTask

                // Update selection if needed
                if selectedTask?.id == task.id {
                    selectedTask = updatedTask
                }
            }
        }

        // Best-effort backend sync
        if let backendTaskId = task.taskId {
            Task {
                do {
                    _ = try await KanbanService.shared.updateTask(
                        taskId: backendTaskId,
                        status: newStatus.rawValue
                    )
                } catch {
                    logger.warning("Failed to sync task status to backend: \(error.localizedDescription)")
                }
            }
        }
    }

    // MARK: - Drag & Drop

    private func statusSectionHeader(_ status: TaskStatus, count: Int) -> some View {
        HStack(spacing: 8) {
            Image(systemName: status.icon)
                .font(.system(size: 12))
                .foregroundStyle(status.color)
            Text(status.rawValue)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.secondary)
            Text("\(count)")
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Capsule().fill(Color.gray.opacity(0.15)))
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(dropTargetStatus == status ? status.color.opacity(0.1) : Color.clear)
        .overlay {
            if dropTargetStatus == status {
                RoundedRectangle(cornerRadius: 6)
                    .stroke(status.color, lineWidth: 2)
            }
        }
        .accessibilityLabel("\(status.rawValue) section, \(count) tasks")
        .accessibilityHint("Drop task here to change status")
    }

    private func handleTaskDrop(_ items: [String], to status: TaskStatus) {
        for idString in items {
            guard let uuid = UUID(uuidString: idString),
                  let task = dataManager.tasks.first(where: { $0.id == uuid }),
                  task.status != status else { continue }
            updateTaskStatus(task, to: status)
        }
    }

    private func updateTaskPriority(_ task: KanbanTask, to newPriority: TaskPriority) {
        // Update locally for immediate feedback
        withAnimation(.magnetarQuick) {
            if let index = dataManager.tasks.firstIndex(where: { $0.id == task.id }) {
                let updatedTask = KanbanTask(
                    title: task.title,
                    description: task.description,
                    status: task.status,
                    priority: newPriority,
                    assignee: task.assignee,
                    dueDate: task.dueDate,
                    labels: task.labels,
                    taskId: task.taskId,
                    boardId: task.boardId,
                    columnId: task.columnId
                )
                dataManager.tasks[index] = updatedTask

                // Update selection if needed
                if selectedTask?.id == task.id {
                    selectedTask = updatedTask
                }
            }
        }

        // Best-effort backend sync
        if let backendTaskId = task.taskId {
            Task {
                do {
                    _ = try await KanbanService.shared.updateTask(
                        taskId: backendTaskId,
                        priority: newPriority.rawValue
                    )
                } catch {
                    logger.warning("Failed to sync task priority to backend: \(error.localizedDescription)")
                }
            }
        }
    }
}

#Preview {
    KanbanWorkspace()
}
