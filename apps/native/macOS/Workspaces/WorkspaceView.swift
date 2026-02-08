//
//  WorkspaceView.swift
//  MagnetarStudio (macOS)
//
//  Unified Workspace - personal notes + team chat in one clean view
//  Team features controlled via popover at bottom of sidebar
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "WorkspaceView")

// MARK: - Workspace View

struct WorkspaceView: View {
    @AppStorage("workspace.teamEnabled") private var teamEnabled = false
    @AppStorage("workspace.connectionMode") private var connectionMode = "cloud"
    @State private var selectedNote: PersonalNote?
    @State private var selectedChannel: String?
    @State private var notes: [PersonalNote] = []
    @State private var editorContent = ""
    @State private var messageText = ""
    @State private var showSettingsPopover = false
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        HStack(spacing: 0) {
            // Unified sidebar
            sidebar

            Divider()

            // Content area - either note editor or chat
            contentArea
        }
        .task {
            await loadNotes()
        }
    }

    // MARK: - Sidebar

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Notes section (always visible)
            sidebarSection(title: "Notes", showAdd: true, onAdd: createNewNote) {
                ForEach(notes) { note in
                    NoteRow(
                        note: note,
                        isSelected: selectedNote?.id == note.id && selectedChannel == nil
                    ) {
                        selectedNote = note
                        selectedChannel = nil
                        editorContent = note.content
                    }
                }

                if notes.isEmpty {
                    Text("No notes yet")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                }
            }

            // Team sections (only if team enabled)
            if teamEnabled {
                sidebarSection(title: "Channels", showAdd: true, onAdd: {}) {
                    ChannelRow(name: "general", isSelected: selectedChannel == "general") {
                        selectedChannel = "general"
                        selectedNote = nil
                    }
                    ChannelRow(name: "random", isSelected: selectedChannel == "random") {
                        selectedChannel = "random"
                        selectedNote = nil
                    }
                }

                sidebarSection(title: "Direct Messages", showAdd: false, onAdd: {}) {
                    Text("No conversations yet")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                }
            }

            Spacer()

            // Bottom: Connection status + settings
            bottomBar
        }
        .frame(width: 230)
        .background(Color.gray.opacity(0.03))
    }

    private func sidebarSection<Content: View>(
        title: String,
        showAdd: Bool,
        onAdd: @escaping () -> Void,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(title.uppercased())
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                if showAdd {
                    Button(action: onAdd) {
                        Image(systemName: "plus")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.top, 16)
            .padding(.bottom, 6)

            content()
        }
    }

    // MARK: - Connection Label

    private var connectionLabel: String {
        switch connectionMode {
        case "cloud": return "Cloud"
        case "wifi-aware": return "WiFi Aware"
        case "p2p": return "P2P"
        case "lan": return "LAN"
        default: return "Connected"
        }
    }

    // MARK: - Bottom Bar (Status + Settings)

    private var bottomBar: some View {
        HStack(spacing: 8) {
            // Connection status
            Circle()
                .fill(teamEnabled ? Color.green : Color.gray)
                .frame(width: 8, height: 8)

            Text(teamEnabled ? connectionLabel : "Personal")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)

            Spacer()

            // Settings button
            Button {
                showSettingsPopover.toggle()
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)
                    .frame(width: 24, height: 24)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.1))
                    )
            }
            .buttonStyle(.plain)
            .popover(isPresented: $showSettingsPopover, arrowEdge: .bottom) {
                WorkspaceSettingsPopover(
                    teamEnabled: $teamEnabled,
                    onOpenSettings: {
                        showSettingsPopover = false
                        openWindow(id: "workspace-settings")
                    }
                )
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        if let channel = selectedChannel {
            // Chat view
            chatView(channel: channel)
        } else if let note = selectedNote {
            // Note editor
            noteEditorView(note: note)
        } else {
            // Empty state
            emptyStateView
        }
    }

    private func noteEditorView(note: PersonalNote) -> some View {
        VStack(spacing: 0) {
            // Header - minimal, no toolbar
            HStack {
                Text(note.title)
                    .font(.headline)
                Spacer()
                Text("Type / for commands")
                    .font(.caption)
                    .foregroundStyle(.secondary.opacity(0.6))
                Text("•")
                    .foregroundStyle(.secondary.opacity(0.3))
                Text("Saved")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color.gray.opacity(0.03))

            Divider()

            // Notion-style editor with slash commands
            WorkspaceEditor(content: $editorContent)
                .onChange(of: editorContent) { _, newValue in
                    saveNote(content: newValue)
                }
        }
    }

    private func chatView(channel: String) -> some View {
        VStack(spacing: 0) {
            // Channel header
            HStack {
                Text("#")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.secondary)
                Text(channel)
                    .font(.system(size: 15, weight: .semibold))
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.03))

            Divider()

            // Messages
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    MessageBubble(
                        author: "System",
                        message: "Welcome to #\(channel)! This is the start of the conversation.",
                        time: "Today"
                    )
                }
                .padding(16)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            Divider()

            // Input
            HStack(spacing: 12) {
                TextField("Message #\(channel)...", text: $messageText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))

                Button {
                    // Send
                } label: {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 14))
                        .foregroundStyle(messageText.isEmpty ? .secondary : Color.accentColor)
                }
                .buttonStyle(.plain)
                .disabled(messageText.isEmpty)
            }
            .padding(12)
            .background(Color.gray.opacity(0.05))
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "doc.text")
                .font(.system(size: 48))
                .foregroundStyle(.secondary.opacity(0.4))
            Text("Select a note or channel")
                .font(.body)
                .foregroundStyle(.secondary)
            Button("New Note") {
                createNewNote()
            }
            .buttonStyle(.borderedProminent)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Data

    private func loadNotes() async {
        notes = [
            PersonalNote(id: "1", title: "Welcome to Workspace", content: "This is your personal notes space.\n\nUse it to capture ideas, write documents, or just jot things down.", updatedAt: Date()),
            PersonalNote(id: "2", title: "Quick Tips", content: "- Create new notes with the + button\n- Enable Team mode for channels and DMs\n- Your notes sync across devices", updatedAt: Date().addingTimeInterval(-3600))
        ]
        if let first = notes.first {
            selectedNote = first
            editorContent = first.content
        }
    }

    private func createNewNote() {
        let newNote = PersonalNote(
            id: UUID().uuidString,
            title: "Untitled",
            content: "",
            updatedAt: Date()
        )
        notes.insert(newNote, at: 0)
        selectedNote = newNote
        selectedChannel = nil
        editorContent = ""
    }

    private func saveNote(content: String) {
        guard var note = selectedNote,
              let index = notes.firstIndex(where: { $0.id == note.id }) else { return }
        note.content = content
        note.updatedAt = Date()
        notes[index] = note
        selectedNote = note
    }
}

// MARK: - Settings Popover

struct WorkspaceSettingsPopover: View {
    @Binding var teamEnabled: Bool
    let onOpenSettings: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Team toggle
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Team Mode")
                        .font(.system(size: 13, weight: .medium))
                    Text(teamEnabled ? "Channels & DMs enabled" : "Personal only")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Toggle("", isOn: $teamEnabled)
                    .toggleStyle(.switch)
                    .controlSize(.small)
            }
            .padding(12)

            Divider()

            // Connection status
            if teamEnabled {
                HStack(spacing: 8) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                    Text("Connected")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("Cloud")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color.gray.opacity(0.15))
                        )
                }
                .padding(12)

                Divider()
            }

            // Open full settings
            Button {
                onOpenSettings()
            } label: {
                HStack {
                    Text("Connection Settings...")
                        .font(.system(size: 12))
                    Spacer()
                    Image(systemName: "arrow.up.forward.square")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .padding(12)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
        .frame(width: 220)
    }
}

// MARK: - Supporting Views

struct PersonalNote: Identifiable, Equatable {
    let id: String
    var title: String
    var content: String
    var updatedAt: Date
}

struct NoteRow: View {
    let note: PersonalNote
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(note.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)
                    Spacer()
                    Text(formatTimestamp(note.updatedAt))
                        .font(.system(size: 10))
                        .foregroundStyle(isSelected ? .white.opacity(0.6) : .secondary.opacity(0.7))
                }
                Text(note.content.prefix(60).replacingOccurrences(of: "\n", with: " "))
                    .font(.system(size: 11))
                    .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(isSelected ? Color.accentColor : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
    }

    private func formatTimestamp(_ date: Date) -> String {
        let diff = Date().timeIntervalSince(date)
        if diff < 60 { return "now" }
        else if diff < 3600 { return "\(Int(diff / 60))m" }
        else if diff < 86400 { return "\(Int(diff / 3600))h" }
        else { return "\(Int(diff / 86400))d" }
    }
}

struct ChannelRow: View {
    let name: String
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 6) {
                Text("#")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)
                Text(name)
                    .font(.system(size: 13))
                    .foregroundStyle(isSelected ? .white : .primary)
                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .fill(isSelected ? Color.accentColor : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
    }
}

struct MessageBubble: View {
    let author: String
    let message: String
    let time: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(Color.gray.opacity(0.3))
                .frame(width: 36, height: 36)
                .overlay(
                    Text(String(author.prefix(1)))
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(.secondary)
                )
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(author)
                        .font(.system(size: 13, weight: .semibold))
                    Text(time)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                Text(message)
                    .font(.system(size: 14))
            }
            Spacer()
        }
    }
}

// MARK: - Preview

#Preview {
    WorkspaceView()
        .frame(width: 900, height: 600)
}
