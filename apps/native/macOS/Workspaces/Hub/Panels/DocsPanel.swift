//
//  DocsPanel.swift
//  MagnetarStudio
//
//  Document editor panel — Notion + Word + Quip hybrid.
//  Rich formatting toolbar, page-style layout, and document management.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DocsPanel")

struct DocsPanel: View {
    @State private var documents: [WorkspaceDocument] = []
    @State private var selectedDocID: UUID?
    @State private var editorContent = ""
    @State private var searchText = ""
    @FocusState private var isSearchFocused: Bool
    @State private var isLoading = true
    @State private var showDocsList = true
    @State private var collaborators: [CollaboratorPresence] = []
    @AppStorage("workspace.teamEnabled") private var teamEnabled = false

    var body: some View {
        HStack(spacing: 0) {
            // Document list (collapsible)
            if showDocsList {
                docsList
                    .frame(width: 240)
                Divider()
            }

            // Editor area
            if let docID = selectedDocID,
               let docIndex = documents.firstIndex(where: { $0.id == docID }) {
                VStack(spacing: 0) {
                    DocsToolbar(
                        document: $documents[docIndex],
                        showDocsList: $showDocsList
                    )

                    // Team collab indicator
                    TeamCollabIndicator(
                        collaborators: collaborators,
                        documentTitle: documents[docIndex].title
                    )

                    Divider()

                    // Page-style editor container
                    ScrollView {
                        VStack(spacing: 0) {
                            // Document title
                            documentTitleField(at: docIndex)

                            // Editor content
                            WorkspaceEditor(content: $editorContent)
                                .onChange(of: editorContent) { _, newValue in
                                    saveDocument(at: docIndex, content: newValue)
                                }
                        }
                        .frame(maxWidth: 750)
                        .padding(.horizontal, 40)
                        .padding(.vertical, 24)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.surfacePrimary)

                    // Status bar
                    docStatusBar(at: docIndex)
                }
            } else {
                docsEmptyState
            }
        }
        .task {
            await loadDocuments()
        }
    }

    // MARK: - Document Title

    private func documentTitleField(at index: Int) -> some View {
        TextField("Untitled Document", text: $documents[index].title)
            .font(.system(size: 28, weight: .bold))
            .textFieldStyle(.plain)
            .padding(.bottom, 8)
    }

    // MARK: - Status Bar

    private func docStatusBar(at index: Int) -> some View {
        HStack(spacing: 16) {
            Text("\(documents[index].wordCount) words")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)

            Divider().frame(height: 12)

            Text(formatDate(documents[index].updatedAt))
                .font(.system(size: 11))
                .foregroundStyle(.secondary)

            Spacer()

            Text("Type / for commands")
                .font(.system(size: 11))
                .foregroundStyle(.quaternary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 6)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

    // MARK: - Documents List

    private var docsList: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                TextField("Search docs...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .focused($isSearchFocused)

                if !searchText.isEmpty {
                    Button { searchText = "" } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear search")
                }

                Button(action: createDocument) {
                    Image(systemName: "doc.badge.plus")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("New Document")
                .accessibilityLabel("New Document")
            }
            .padding(.horizontal, 12)
            .frame(height: HubLayout.headerHeight)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            // Document list
            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredDocs.isEmpty {
                VStack(spacing: 8) {
                    Text(searchText.isEmpty ? "No documents" : "No results")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    if searchText.isEmpty {
                        Button("New Document") { createDocument() }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        // Starred section
                        let starred = filteredDocs.filter(\.isStarred)
                        if !starred.isEmpty {
                            docSectionHeader("Starred")
                            ForEach(starred) { doc in
                                DocListRow(
                                    document: doc,
                                    isSelected: selectedDocID == doc.id,
                                    onSelect: { selectDocument(doc) },
                                    onStar: { toggleStar(doc) },
                                    onDelete: { deleteDocument(doc) }
                                )
                            }
                        }

                        // All documents
                        let unstarred = filteredDocs.filter { !$0.isStarred }
                        if !unstarred.isEmpty {
                            if !starred.isEmpty {
                                docSectionHeader("Documents")
                            }
                            ForEach(unstarred) { doc in
                                DocListRow(
                                    document: doc,
                                    isSelected: selectedDocID == doc.id,
                                    onSelect: { selectDocument(doc) },
                                    onStar: { toggleStar(doc) },
                                    onDelete: { deleteDocument(doc) }
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

    private func docSectionHeader(_ title: String) -> some View {
        Text(title.uppercased())
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 14)
            .padding(.top, 12)
            .padding(.bottom, 4)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var docsEmptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.richtext")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Create or select a document")
                .font(.body)
                .foregroundStyle(.secondary)
            Button("New Document") { createDocument() }
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Filtered Documents

    private var filteredDocs: [WorkspaceDocument] {
        let sorted = documents.sorted { a, b in
            if a.isStarred != b.isStarred { return a.isStarred }
            return a.updatedAt > b.updatedAt
        }
        if searchText.isEmpty { return sorted }
        let query = searchText.lowercased()
        return sorted.filter {
            $0.title.lowercased().contains(query) || $0.content.lowercased().contains(query)
        }
    }

    // MARK: - Actions

    private func createDocument() {
        let doc = WorkspaceDocument()
        documents.insert(doc, at: 0)
        selectDocument(doc)
        saveDocToDisk(doc)
    }

    private func selectDocument(_ doc: WorkspaceDocument) {
        selectedDocID = doc.id
        editorContent = doc.content
    }

    private func saveDocument(at index: Int, content: String) {
        guard documents.indices.contains(index) else { return }
        documents[index].updateContent(content)
        saveDocToDisk(documents[index])

        // Fire automation trigger
        AutomationTriggerService.shared.documentSaved(title: documents[index].title, content: content)
    }

    private func toggleStar(_ doc: WorkspaceDocument) {
        guard let index = documents.firstIndex(where: { $0.id == doc.id }) else { return }
        documents[index].isStarred.toggle()
        saveDocToDisk(documents[index])
    }

    private func deleteDocument(_ doc: WorkspaceDocument) {
        documents.removeAll { $0.id == doc.id }
        if selectedDocID == doc.id {
            selectedDocID = documents.first?.id
        }
        deleteDocFromDisk(doc)
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/docs", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "docs storage")
        return dir
    }

    private func loadDocuments() async {
        defer { isLoading = false }
        let dir = Self.storageDir
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension == "json" }
        } catch {
            logger.error("Failed to list docs directory: \(error.localizedDescription)")
            return
        }

        var loaded: [WorkspaceDocument] = []
        for file in files {
            if let doc = PersistenceHelpers.load(WorkspaceDocument.self, from: file, label: "document") {
                loaded.append(doc)
            }
        }

        if loaded.isEmpty {
            let welcome = WorkspaceDocument(
                title: "Getting Started",
                content: "Welcome to Docs\n\nThis is your document workspace. Create rich documents with formatting, headings, lists, code blocks, and more.\n\nUse the / slash command to insert different block types.\n\nDocs support:\n- Rich text editing with the block editor\n- Word count tracking\n- Star important documents\n- Search across all documents"
            )
            loaded.append(welcome)
            saveDocToDisk(welcome)
        }

        documents = loaded.sorted { $0.updatedAt > $1.updatedAt }
        selectedDocID = documents.first?.id
        if let first = documents.first {
            editorContent = first.content
        }
    }

    private func saveDocToDisk(_ doc: WorkspaceDocument) {
        let file = Self.storageDir.appendingPathComponent("\(doc.id.uuidString).json")
        PersistenceHelpers.save(doc, to: file, label: "document '\(doc.title)'")
    }

    private func deleteDocFromDisk(_ doc: WorkspaceDocument) {
        let file = Self.storageDir.appendingPathComponent("\(doc.id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "document '\(doc.title)'")
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.doesRelativeDateFormatting = true
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

// MARK: - Document List Row

private struct DocListRow: View {
    let document: WorkspaceDocument
    let isSelected: Bool
    let onSelect: () -> Void
    let onStar: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: "doc.richtext")
                    .font(.system(size: 14))
                    .foregroundStyle(isSelected ? .white : .secondary)
                    .frame(width: 20)

                VStack(alignment: .leading, spacing: 2) {
                    HStack {
                        if document.isStarred {
                            Image(systemName: "star.fill")
                                .font(.system(size: 9))
                                .foregroundStyle(.yellow)
                        }
                        Text(document.title)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(isSelected ? .white : .primary)
                            .lineLimit(1)
                    }
                    Text("\(document.wordCount) words")
                        .font(.system(size: 10))
                        .foregroundStyle(isSelected ? .white.opacity(0.6) : .secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
        .contextMenu {
            Button(document.isStarred ? "Unstar" : "Star") { onStar() }
            Divider()
            Button("Delete", role: .destructive) { onDelete() }
        }
    }
}
