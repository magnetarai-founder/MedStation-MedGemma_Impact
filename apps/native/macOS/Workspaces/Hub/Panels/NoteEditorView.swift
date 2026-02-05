//
//  NoteEditorView.swift
//  MagnetarStudio
//
//  Wrapper around WorkspaceEditor for editing a single note.
//  Adds title field, metadata bar, and autosave.
//

import SwiftUI

struct NoteEditorView: View {
    @Binding var note: WorkspaceNote
    let onContentChange: (String) -> Void

    @State private var editableContent: String = ""
    @State private var isEditingTitle = false
    @State private var showAIAssist = false
    @FocusState private var titleFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Header
            noteHeader

            Divider()

            // Editor
            WorkspaceEditor(content: $editableContent)
                .onChange(of: editableContent) { _, newValue in
                    onContentChange(newValue)
                }
        }
        .background(Color.surfacePrimary)
        .onAppear {
            editableContent = note.content
        }
        .onChange(of: note.id) { _, _ in
            editableContent = note.content
        }
    }

    // MARK: - Header

    private var noteHeader: some View {
        HStack(spacing: 12) {
            // Editable title
            if isEditingTitle {
                TextField("Note title", text: $note.title)
                    .font(.system(size: 15, weight: .semibold))
                    .textFieldStyle(.plain)
                    .focused($titleFocused)
                    .onSubmit { isEditingTitle = false }
            } else {
                Text(note.title)
                    .font(.system(size: 15, weight: .semibold))
                    .onTapGesture {
                        isEditingTitle = true
                        titleFocused = true
                    }
            }

            Spacer()

            // Metadata
            if note.isPinned {
                Image(systemName: "pin.fill")
                    .font(.system(size: 10))
                    .foregroundStyle(.orange)
            }

            Button {
                showAIAssist.toggle()
            } label: {
                Image(systemName: "sparkles")
                    .font(.system(size: 12))
                    .foregroundStyle(.purple)
                    .frame(width: 26, height: 26)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.purple.opacity(0.1))
                    )
            }
            .buttonStyle(.plain)
            .help("AI Assist (⌘⇧I)")
            .popover(isPresented: $showAIAssist) {
                AIAssistPopover(
                    inputText: editableContent,
                    context: note.title,
                    onAccept: { result in
                        editableContent = result
                        onContentChange(result)
                        showAIAssist = false
                    },
                    onDismiss: {
                        showAIAssist = false
                    }
                )
            }

            Text("Type / for commands")
                .font(.system(size: 11))
                .foregroundStyle(.quaternary)

            Text(formatDate(note.updatedAt))
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.doesRelativeDateFormatting = true
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}
