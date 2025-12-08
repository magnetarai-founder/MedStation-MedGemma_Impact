//
//  DocsWorkspaceView.swift
//  MagnetarStudio (macOS)
//
//  Team documents workspace with editor and sidebar - Extracted from TeamWorkspace.swift
//

import SwiftUI

struct DocsWorkspace: View {
    @State private var sidebarVisible: Bool = true
    @State private var activeDocument: TeamDocument? = nil
    @State private var documents: [TeamDocument] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var showNewDocumentModal: Bool = false
    @State private var showEditDocumentModal: Bool = false
    @State private var documentToEdit: TeamDocument? = nil

    private let teamService = TeamService.shared

    var body: some View {
        HStack(spacing: 0) {
            // Left Sidebar - Documents list
            if sidebarVisible {
                VStack(spacing: 0) {
                    // Sidebar header
                    HStack(spacing: 12) {
                        Image(systemName: "doc.text.fill")
                            .font(.system(size: 18))
                            .foregroundColor(Color.magnetarPrimary)

                        VStack(alignment: .leading, spacing: 2) {
                            Text("Documents")
                                .font(.system(size: 16, weight: .semibold))

                            Text("\(documents.count) document\(documents.count == 1 ? "" : "s")")
                                .font(.system(size: 12))
                                .foregroundColor(.secondary)
                        }

                        Spacer()

                        Button(action: { showNewDocumentModal = true }) {
                            Image(systemName: "plus")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                                .frame(width: 32, height: 32)
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(Color(.controlBackgroundColor))
                    .overlay(
                        Rectangle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(height: 1),
                        alignment: .bottom
                    )

                    ScrollView {
                        VStack(alignment: .leading, spacing: 12) {
                            // Documents section header
                            HStack {
                                Text("DOCUMENTS")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(.secondary)
                                    .textCase(.uppercase)

                                Spacer()
                            }
                            .padding(.bottom, 4)

                            // Document list
                            ForEach(documents) { doc in
                                DocumentRowView(
                                    doc: doc,
                                    isActive: activeDocument?.id == doc.id,
                                    onSelect: { activeDocument = doc },
                                    onEdit: {
                                        documentToEdit = doc
                                        showEditDocumentModal = true
                                    },
                                    onDelete: {
                                        Task {
                                            await deleteDocument(doc)
                                        }
                                    }
                                )
                            }
                        }
                        .padding(.horizontal, 8)
                        .padding(.top, 16)
                        .padding(.bottom, 8)
                    }
                }
                .frame(width: 256)

                Divider()
            }

            // Main area
            if isLoading {
                loadingView
            } else if let error = errorMessage {
                errorView(error)
            } else if let doc = activeDocument {
                documentEditor(doc: doc)
            } else {
                emptyState
            }
        }
        .task {
            await loadDocuments()
        }
        .sheet(isPresented: $showNewDocumentModal) {
            NewDocumentModal(isPresented: $showNewDocumentModal) { title, type in
                try await createDocument(title: title, type: type)
            }
        }
        .sheet(isPresented: $showEditDocumentModal) {
            if let doc = documentToEdit {
                EditDocumentModal(
                    isPresented: $showEditDocumentModal,
                    document: doc
                ) { newTitle in
                    try await updateDocument(doc, newTitle: newTitle)
                }
            }
        }
    }

    @MainActor
    private func loadDocuments() async {
        isLoading = true
        errorMessage = nil

        do {
            documents = try await teamService.listDocuments()
            // Auto-select first document if none selected
            if activeDocument == nil && !documents.isEmpty {
                activeDocument = documents.first
            }
            isLoading = false
        } catch ApiError.unauthorized {
            print("⚠️ Unauthorized when loading documents - session may not be initialized yet")
            // Don't show error to user for auth issues - they just logged in
            documents = []
            isLoading = false
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    @MainActor
    private func createDocument(title: String, type: NewDocumentType) async throws {
        let newDoc = try await teamService.createDocument(
            title: title,
            content: "",
            type: type.backendType
        )
        documents.append(newDoc)
        activeDocument = newDoc
        await loadDocuments() // Refresh list
    }

    @MainActor
    private func updateDocument(_ doc: TeamDocument, newTitle: String) async throws {
        let updated = try await teamService.updateDocument(id: doc.id, title: newTitle, content: nil)
        if let index = documents.firstIndex(where: { $0.id == doc.id }) {
            documents[index] = updated
            if activeDocument?.id == doc.id {
                activeDocument = updated
            }
        }
    }

    @MainActor
    private func deleteDocument(_ doc: TeamDocument) async {
        do {
            try await teamService.deleteDocument(id: doc.id)
            documents.removeAll { $0.id == doc.id }
            if activeDocument?.id == doc.id {
                activeDocument = documents.first
            }
        } catch {
            errorMessage = "Failed to delete document: \(error.localizedDescription)"
        }
    }

    // MARK: - Helper Views

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)

            Text("Loading documents...")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.red)

            Text("Error Loading Documents")
                .font(.system(size: 18, weight: .semibold))

            Text(message)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button("Retry") {
                Task {
                    await loadDocuments()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    private func documentEditor(doc: TeamDocument) -> some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 12) {
                Button {
                    sidebarVisible.toggle()
                } label: {
                    Image(systemName: "sidebar.left")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)

                VStack(alignment: .leading, spacing: 2) {
                    Text(doc.title)
                        .font(.system(size: 16, weight: .semibold))

                    Text("Last edited: \(doc.updatedAt)")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Editor area - showing content
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(doc.content?.stringValue ?? doc.content?.value as? String ?? "No content")
                        .font(.system(size: 14))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "plus")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("No document selected")
                .font(.system(size: 18, weight: .semibold))

            Text("Select a document from the sidebar or create a new one")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Documents Sidebar

struct DocumentsSidebar: View {
    @Binding var activeDocument: TeamDocument?
    let documents: [TeamDocument]

    var body: some View {
        if documents.isEmpty {
            VStack(spacing: 12) {
                Image(systemName: "doc.text")
                    .font(.system(size: 32))
                    .foregroundColor(.secondary)

                Text("No documents yet")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
        } else {
            ScrollView {
                VStack(spacing: 4) {
                    ForEach(documents) { doc in
                        documentRow(doc: doc, isActive: activeDocument?.id == doc.id)
                            .onTapGesture {
                                activeDocument = doc
                            }
                    }
                }
                .padding(8)
            }
        }
    }

    private func documentRow(doc: TeamDocument, isActive: Bool) -> some View {
        HStack(spacing: 10) {
            Image(systemName: iconForType(doc.type))
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title)
                    .font(.system(size: 13, weight: isActive ? .medium : .regular))
                    .foregroundColor(isActive ? .primary : .secondary)

                Text(doc.updatedAt)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
        )
    }

    private func iconForType(_ type: String) -> String {
        switch type.lowercased() {
        case "document": return "doc.text"
        case "spreadsheet": return "tablecells"
        case "insight": return "chart.bar.doc.horizontal"
        case "securedocument", "secure_document": return "lock.doc"
        default: return "doc"
        }
    }
}

// MARK: - Document Types

enum DocumentType: String {
    case document = "document"
    case spreadsheet = "spreadsheet"
    case insight = "insight"
    case secureDocument = "secure_document"

    var displayName: String {
        switch self {
        case .document: return "Document"
        case .spreadsheet: return "Spreadsheet"
        case .insight: return "Insight"
        case .secureDocument: return "Secure Document"
        }
    }

    var icon: String {
        switch self {
        case .document: return "doc.text"
        case .spreadsheet: return "tablecells"
        case .insight: return "chart.bar.doc.horizontal"
        case .secureDocument: return "lock.doc"
        }
    }
}

struct Document: Identifiable {
    let id = UUID()
    let name: String
    let type: DocumentType
    let lastEdited: String

    static let mockDocuments = [
        Document(name: "Project Proposal", type: .document, lastEdited: "2 hours ago"),
        Document(name: "Q4 Budget", type: .spreadsheet, lastEdited: "Yesterday"),
        Document(name: "Sales Analysis", type: .insight, lastEdited: "3 days ago"),
        Document(name: "Confidential Report", type: .secureDocument, lastEdited: "Last week")
    ]
}

// MARK: - Document Row with Hover Actions

struct DocumentRowView: View {
    let doc: TeamDocument
    let isActive: Bool
    let onSelect: () -> Void
    let onEdit: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: iconForType(doc.type))
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title)
                    .font(.system(size: 13, weight: isActive ? .medium : .regular))
                    .foregroundColor(isActive ? .primary : .secondary)
                    .lineLimit(1)

                Text(formatDate(doc.updatedAt))
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Show actions on hover
            if isHovered {
                HStack(spacing: 4) {
                    Button(action: onEdit) {
                        Image(systemName: "pencil")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                            .frame(width: 24, height: 24)
                    }
                    .buttonStyle(.plain)

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 12))
                            .foregroundColor(.red)
                            .frame(width: 24, height: 24)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.1) : (isHovered ? Color.gray.opacity(0.05) : Color.clear))
        )
        .contentShape(Rectangle())
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            isHovered = hovering
        }
    }

    private func iconForType(_ type: String) -> String {
        switch type.lowercased() {
        case "document": return "doc.text"
        case "spreadsheet": return "tablecells"
        case "insight": return "chart.bar.doc.horizontal"
        case "securedocument", "secure_document": return "lock.doc"
        default: return "doc"
        }
    }

    private func formatDate(_ dateString: String) -> String {
        // Simple formatter - just show the date part for now
        if let range = dateString.range(of: "T") {
            return String(dateString[..<range.lowerBound])
        }
        return dateString
    }
}
