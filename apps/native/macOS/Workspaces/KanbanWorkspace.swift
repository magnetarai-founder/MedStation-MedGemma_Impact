//
//  KanbanWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Kanban task management workspace with three-pane Outlook-style layout.
//  Refactored in Phase 6.20 - extracted detail pane, data manager, and CRUD operations
//

import SwiftUI

struct KanbanWorkspace: View {
    @State private var selectedBoard: KanbanBoard? = nil
    @State private var selectedTask: KanbanTask? = nil
    @State private var showNewBoardSheet = false
    @State private var showNewTaskSheet = false
    @State private var boardToDelete: KanbanBoard? = nil
    @State private var taskToDelete: KanbanTask? = nil
    @State private var newBoardName = ""
    @State private var newTaskTitle = ""

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
                        ForEach(dataManager.tasks) { task in
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
}

#Preview {
    KanbanWorkspace()
}
