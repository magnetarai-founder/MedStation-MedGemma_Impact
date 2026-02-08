//
//  KanbanModals.swift
//  MagnetarStudio (macOS)
//
//  New board and task sheet modals - Extracted from KanbanWorkspace.swift
//

import SwiftUI

// MARK: - New Board Sheet

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
                        .foregroundStyle(.secondary)
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

// MARK: - New Task Sheet

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
                        .foregroundStyle(.secondary)
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
