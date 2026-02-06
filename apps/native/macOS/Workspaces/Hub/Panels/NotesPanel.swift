//
//  NotesPanel.swift
//  MagnetarStudio
//
//  Personal notes panel for the Workspace Hub.
//  Slack-like workspace for individual note-taking with the
//  Notion-style WorkspaceEditor.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "NotesPanel")

// MARK: - Data Model

struct WorkspaceNote: Identifiable, Codable, Equatable, Hashable, Sendable {
    let id: UUID
    var title: String
    var content: String
    var createdAt: Date
    var updatedAt: Date
    var isPinned: Bool
    var tags: [String]

    init(
        id: UUID = UUID(),
        title: String = "Untitled",
        content: String = "",
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        isPinned: Bool = false,
        tags: [String] = []
    ) {
        self.id = id
        self.title = title
        self.content = content
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.isPinned = isPinned
        self.tags = tags
    }
}

// MARK: - Notes Panel

struct NotesPanel: View {
    @State private var notes: [WorkspaceNote] = []
    @State private var selectedNoteID: UUID?
    @State private var editorContent = ""
    @State private var searchText = ""
    @State private var isLoading = true
    @State private var showTemplatePicker = false
    @State private var selectedTemplate: WorkspaceTemplate?
    var body: some View {
        HStack(spacing: 0) {
            // Notes list
            notesList
                .frame(width: 240)

            Divider()

            // Editor
            if let noteID = selectedNoteID,
               let noteIndex = notes.firstIndex(where: { $0.id == noteID }) {
                NoteEditorView(
                    note: $notes[noteIndex],
                    onContentChange: { newContent in
                        saveNote(at: noteIndex, content: newContent)
                    }
                )
            } else {
                emptyState
            }
        }
        .task {
            await loadNotes()
        }
        .sheet(isPresented: $showTemplatePicker) {
            TemplatePickerSheet(
                targetPanel: .note,
                onBlank: {
                    showTemplatePicker = false
                    createNote()
                },
                onTemplate: { template in
                    showTemplatePicker = false
                    selectedTemplate = template
                },
                onDismiss: { showTemplatePicker = false }
            )
        }
        .sheet(item: $selectedTemplate) { template in
            TemplateFillSheet(
                template: template,
                onConfirm: { title, variables in
                    let note = TemplateStore.shared.instantiateAsNote(
                        template: template,
                        title: title,
                        variables: variables
                    )
                    notes.insert(note, at: 0)
                    selectNote(note)
                    saveNoteToDisk(note)
                    selectedTemplate = nil
                },
                onCancel: { selectedTemplate = nil }
            )
        }
    }

    // MARK: - Notes List

    private var notesList: some View {
        VStack(spacing: 0) {
            // Search + New Note
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                TextField("Search notes...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))

                Menu {
                    Button("Blank Note") { createNote() }
                    Button("From Template...") { showTemplatePicker = true }
                } label: {
                    Image(systemName: "square.and.pencil")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .menuStyle(.borderlessButton)
                .frame(width: 24)
                .help("New Note")
            }
            .padding(.horizontal, 12)
            .frame(height: HubLayout.headerHeight)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            // Notes
            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredNotes.isEmpty {
                VStack(spacing: 8) {
                    Text(searchText.isEmpty ? "No notes yet" : "No results")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    if searchText.isEmpty {
                        Button("Create Note") { createNote() }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        // Pinned section
                        let pinned = filteredNotes.filter(\.isPinned)
                        if !pinned.isEmpty {
                            sectionHeader("Pinned")
                            ForEach(pinned) { note in
                                NoteListRow(
                                    note: note,
                                    isSelected: selectedNoteID == note.id,
                                    onSelect: { selectNote(note) },
                                    onPin: { togglePin(note) },
                                    onDelete: { deleteNote(note) }
                                )
                            }
                        }

                        // All notes
                        let unpinned = filteredNotes.filter { !$0.isPinned }
                        if !unpinned.isEmpty {
                            if !pinned.isEmpty {
                                sectionHeader("Notes")
                            }
                            ForEach(unpinned) { note in
                                NoteListRow(
                                    note: note,
                                    isSelected: selectedNoteID == note.id,
                                    onSelect: { selectNote(note) },
                                    onPin: { togglePin(note) },
                                    onDelete: { deleteNote(note) }
                                )
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceTertiary)
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title.uppercased())
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(.tertiary)
            .padding(.horizontal, 14)
            .padding(.top, 12)
            .padding(.bottom, 4)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "note.text")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Select a note or create a new one")
                .font(.body)
                .foregroundStyle(.secondary)
            Button("New Note") { createNote() }
                .buttonStyle(.borderedProminent)
                .controlSize(.regular)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Filtered Notes

    private var filteredNotes: [WorkspaceNote] {
        if searchText.isEmpty {
            return notes.sorted { a, b in
                if a.isPinned != b.isPinned { return a.isPinned }
                return a.updatedAt > b.updatedAt
            }
        }
        let query = searchText.lowercased()
        return notes
            .filter { $0.title.lowercased().contains(query) || $0.content.lowercased().contains(query) }
            .sorted { $0.updatedAt > $1.updatedAt }
    }

    // MARK: - Actions

    private func createNote() {
        let note = WorkspaceNote()
        notes.insert(note, at: 0)
        selectNote(note)
        saveNoteToDisk(note)
    }

    private func selectNote(_ note: WorkspaceNote) {
        selectedNoteID = note.id
        editorContent = note.content
    }

    private func saveNote(at index: Int, content: String) {
        guard notes.indices.contains(index) else { return }
        notes[index].content = content
        notes[index].updatedAt = Date()

        // Derive title from first line
        let firstLine = content.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? "Untitled"
        if !firstLine.isEmpty && firstLine != notes[index].title {
            notes[index].title = String(firstLine.prefix(60))
        }

        saveNoteToDisk(notes[index])

        // Fire automation trigger
        AutomationTriggerService.shared.documentSaved(title: notes[index].title, content: content)
    }

    private func togglePin(_ note: WorkspaceNote) {
        guard let index = notes.firstIndex(where: { $0.id == note.id }) else { return }
        notes[index].isPinned.toggle()
        saveNoteToDisk(notes[index])
    }

    private func deleteNote(_ note: WorkspaceNote) {
        notes.removeAll { $0.id == note.id }
        if selectedNoteID == note.id {
            selectedNoteID = notes.first?.id
        }
        deleteNoteFromDisk(note)
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/notes", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "notes storage")
        return dir
    }

    private func loadNotes() async {
        defer { isLoading = false }

        let dir = Self.storageDir
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension == "json" }
        } catch {
            logger.error("Failed to list notes directory: \(error.localizedDescription)")
            return
        }

        var loaded: [WorkspaceNote] = []
        for file in files {
            if let note = PersistenceHelpers.load(WorkspaceNote.self, from: file, label: "note") {
                loaded.append(note)
            }
        }

        if loaded.isEmpty {
            // Create welcome note on first launch
            let welcome = WorkspaceNote(
                title: "Welcome to Workspace",
                content: "Welcome to your personal workspace.\n\nThis is where you capture ideas, write documents, and organize your thoughts.\n\nType / for slash commands to add headings, lists, code blocks, and more."
            )
            loaded.append(welcome)
            saveNoteToDisk(welcome)
        }

        notes = loaded.sorted { $0.updatedAt > $1.updatedAt }
        selectedNoteID = notes.first?.id
    }

    private func saveNoteToDisk(_ note: WorkspaceNote) {
        let file = Self.storageDir.appendingPathComponent("\(note.id.uuidString).json")
        PersistenceHelpers.save(note, to: file, label: "note '\(note.title)'")
    }

    private func deleteNoteFromDisk(_ note: WorkspaceNote) {
        let file = Self.storageDir.appendingPathComponent("\(note.id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "note '\(note.title)'")
    }
}

// MARK: - Note List Row

private struct NoteListRow: View {
    let note: WorkspaceNote
    let isSelected: Bool
    let onSelect: () -> Void
    let onPin: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    if note.isPinned {
                        Image(systemName: "pin.fill")
                            .font(.system(size: 9))
                            .foregroundStyle(.orange)
                    }
                    Text(note.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)
                    Spacer()
                    Text(formatTimestamp(note.updatedAt))
                        .font(.system(size: 10))
                        .foregroundColor(isSelected ? .white.opacity(0.6) : .secondary)
                }
                Text(note.content.prefix(80).replacingOccurrences(of: "\n", with: " "))
                    .font(.system(size: 11))
                    .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
        .contextMenu {
            Button(note.isPinned ? "Unpin" : "Pin") { onPin() }
            Divider()
            Button("Delete", role: .destructive) { onDelete() }
        }
    }

    private func formatTimestamp(_ date: Date) -> String {
        let diff = Date().timeIntervalSince(date)
        if diff < 60 { return "now" }
        else if diff < 3600 { return "\(Int(diff / 60))m" }
        else if diff < 86400 { return "\(Int(diff / 3600))h" }
        else { return "\(Int(diff / 86400))d" }
    }
}
