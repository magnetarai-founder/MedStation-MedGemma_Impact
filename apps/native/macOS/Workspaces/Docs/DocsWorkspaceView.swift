//
//  DocsWorkspaceView.swift
//  MagnetarStudio (macOS)
//
//  Team documents workspace with editor and sidebar
//  Refactored in Phase 6.21 - extracted sidebar, editor, and data manager
//

import SwiftUI

struct DocsWorkspace: View {
    @State private var sidebarVisible: Bool = true
    @State private var activeDocument: TeamDocument? = nil
    @State private var showNewDocumentModal: Bool = false
    @State private var showEditDocumentModal: Bool = false
    @State private var documentToEdit: TeamDocument? = nil

    // Manager (Phase 6.21)
    @State private var dataManager = DocsDataManager()

    var body: some View {
        HStack(spacing: 0) {
            // Left Sidebar - Documents list
            if sidebarVisible {
                DocsSidebarView(
                    documents: dataManager.documents,
                    activeDocument: activeDocument,
                    onSelectDocument: { doc in
                        activeDocument = doc
                    },
                    onNewDocument: {
                        showNewDocumentModal = true
                    },
                    onEditDocument: { doc in
                        documentToEdit = doc
                        showEditDocumentModal = true
                    },
                    onDeleteDocument: { doc in
                        await dataManager.deleteDocument(doc)
                        // Clear selection if deleted document was selected
                        if activeDocument?.id == doc.id {
                            activeDocument = dataManager.documents.first
                        }
                    }
                )

                Divider()
            }

            // Main area - Editor
            DocsEditorView(
                activeDocument: activeDocument,
                isLoading: dataManager.isLoading,
                errorMessage: dataManager.errorMessage,
                sidebarVisible: $sidebarVisible,
                onRetry: {
                    await loadDocuments()
                }
            )
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

    // MARK: - Data Operations

    @MainActor
    private func loadDocuments() async {
        let firstDoc = await dataManager.loadDocuments()
        // Auto-select first document if none selected
        if activeDocument == nil {
            activeDocument = firstDoc
        }
    }

    @MainActor
    private func createDocument(title: String, type: NewDocumentType) async throws {
        let newDoc = try await dataManager.createDocument(title: title, type: type)
        activeDocument = newDoc
    }

    @MainActor
    private func updateDocument(_ doc: TeamDocument, newTitle: String) async throws {
        let updated = try await dataManager.updateDocument(doc, newTitle: newTitle)
        if activeDocument?.id == doc.id {
            activeDocument = updated
        }
    }
}


// MARK: - Document Row with Hover Actions

struct DocumentRowView: View {
    let doc: TeamDocument
    let isActive: Bool
    let onSelect: () -> Void
    let onEdit: () -> Void
    let onDelete: () -> Void

    @State private var isHovering = false

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "doc.text")
                .font(.system(size: 14))
                .foregroundColor(isActive ? .white : .magnetarPrimary)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(isActive ? .white : .primary)
                    .lineLimit(1)

                Text(doc.updatedAt)
                    .font(.system(size: 11))
                    .foregroundColor(isActive ? Color.white.opacity(0.8) : .secondary)
            }

            Spacer()

            // Hover actions
            if isHovering || isActive {
                HStack(spacing: 4) {
                    Button(action: onEdit) {
                        Image(systemName: "pencil")
                            .font(.system(size: 11))
                            .foregroundColor(isActive ? .white : .secondary)
                            .frame(width: 24, height: 24)
                    }
                    .buttonStyle(.plain)

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 11))
                            .foregroundColor(isActive ? .white : .secondary)
                            .frame(width: 24, height: 24)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isActive ? Color.magnetarPrimary : (isHovering ? Color(.controlBackgroundColor) : Color.clear))
        )
        .contentShape(Rectangle())
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            isHovering = hovering
        }
    }
}
