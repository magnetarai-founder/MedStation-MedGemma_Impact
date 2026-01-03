//
//  DocsDataManager.swift
//  MagnetarStudio (macOS)
//
//  Document data manager - Extracted from DocsWorkspaceView.swift (Phase 6.21)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DocsDataManager")

@MainActor
@Observable
class DocsDataManager {
    var documents: [TeamDocument] = []
    var isLoading: Bool = false
    var errorMessage: String? = nil

    private let teamService = TeamService.shared

    func loadDocuments() async -> TeamDocument? {
        isLoading = true
        errorMessage = nil

        do {
            documents = try await teamService.listDocuments()
            isLoading = false
            // Return first document for auto-selection
            return documents.first
        } catch ApiError.unauthorized {
            logger.warning("Unauthorized when loading documents - session may not be initialized yet")
            // Don't show error to user for auth issues - they just logged in
            documents = []
            isLoading = false
            return nil
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
            return nil
        }
    }

    func createDocument(title: String, type: NewDocumentType) async throws -> TeamDocument {
        let newDoc = try await teamService.createDocument(
            title: title,
            content: "",
            type: type.backendType
        )
        documents.append(newDoc)
        // Refresh list
        _ = await loadDocuments()
        return newDoc
    }

    func updateDocument(_ doc: TeamDocument, newTitle: String) async throws -> TeamDocument {
        let updated = try await teamService.updateDocument(id: doc.id, title: newTitle, content: nil)
        if let index = documents.firstIndex(where: { $0.id == doc.id }) {
            documents[index] = updated
        }
        return updated
    }

    func deleteDocument(_ doc: TeamDocument) async {
        do {
            try await teamService.deleteDocument(id: doc.id)
            documents.removeAll { $0.id == doc.id }
        } catch {
            errorMessage = "Failed to delete document: \(error.localizedDescription)"
        }
    }
}
