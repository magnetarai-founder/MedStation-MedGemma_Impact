//
//  HubModelOperations.swift
//  MagnetarStudio (macOS)
//
//  Model operations manager - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HubModelOperations")

@MainActor
@Observable
class HubModelOperations {
    var activeDownloads: [String: LegacyDownloadProgress] = [:]
    var enrichedModels: [String: EnrichedModelMetadata] = [:]
    var isEnrichingModels: Bool = false
    var errorMessage: String?

    private let ollamaService = OllamaService.shared
    private let enrichmentService = ModelEnrichmentService.shared

    // MARK: - Model Interaction

    func handleModelTap(_ model: AnyModelItem) async {
        // For local models, enrich with AI-generated metadata
        if case .local(let ollamaModel) = model {
            // Check if already enriched
            if enrichedModels[ollamaModel.name] == nil {
                isEnrichingModels = true
                let enriched = await enrichmentService.enrichModel(ollamaModel)
                enrichedModels[ollamaModel.name] = enriched
                isEnrichingModels = false
            }
        }
    }

    // MARK: - Model Downloads

    func downloadModel(modelName: String, ollamaRunning: Bool, networkConnected: Bool, onRefreshModels: @escaping () async -> Void) {
        guard ollamaRunning else {
            errorMessage = "Cannot download - Ollama server not running"
            logger.warning("Cannot download - Ollama server not running")
            return
        }

        guard networkConnected else {
            errorMessage = "Cannot download - No internet connection"
            logger.warning("Cannot download - No internet connection")
            return
        }

        // Clear any previous error
        errorMessage = nil

        // Initialize progress tracking
        activeDownloads[modelName] = LegacyDownloadProgress(
            modelName: modelName,
            status: "Starting download...",
            progress: 0.0
        )

        logger.info("Starting download: \(modelName)")

        ollamaService.pullModel(
            modelName: modelName,
            onProgress: { progress in
                Task { @MainActor in
                    self.activeDownloads[modelName] = LegacyDownloadProgress(
                        modelName: modelName,
                        status: progress.message,
                        progress: self.estimateProgress(from: progress.status)
                    )
                }
            },
            onComplete: { result in
                Task { @MainActor in
                    switch result {
                    case .success:
                        logger.info("Download complete: \(modelName)")
                        self.activeDownloads.removeValue(forKey: modelName)
                        // Refresh local models list
                        await onRefreshModels()
                    case .failure(let error):
                        logger.error("Download failed: \(error.localizedDescription)")
                        self.activeDownloads[modelName] = LegacyDownloadProgress(
                            modelName: modelName,
                            status: "Error: \(error.localizedDescription)",
                            progress: 0.0,
                            error: error.localizedDescription
                        )
                    }
                }
            }
        )
    }

    func deleteModel(_ modelName: String, onRefreshModels: @escaping () async -> Void, onCloseModal: @escaping () -> Void) {
        // Clear any previous error
        errorMessage = nil

        Task {
            do {
                logger.info("Deleting model: \(modelName)")
                let result = try await ollamaService.removeModel(modelName: modelName)
                logger.info("\(result.message)")

                // Refresh local models list
                await onRefreshModels()

                // Clear enrichment cache for this model
                enrichmentService.clearCache(for: modelName)
                enrichedModels.removeValue(forKey: modelName)

                // Close modal
                onCloseModal()
            } catch {
                errorMessage = "Failed to delete model: \(error.localizedDescription)"
                logger.error("Failed to delete model: \(error.localizedDescription)")
            }
        }
    }

    func updateModel(_ modelName: String, ollamaRunning: Bool, networkConnected: Bool, modelsStore: ModelsStore) {
        guard ollamaRunning else {
            errorMessage = "Cannot update - Ollama server not running"
            logger.warning("Cannot update - Ollama server not running")
            return
        }

        guard networkConnected else {
            errorMessage = "Cannot update - No internet connection"
            logger.warning("Cannot update - No internet connection")
            return
        }

        // Clear any previous error
        errorMessage = nil

        // Re-pull the model to update it
        logger.info("Updating model: \(modelName)")

        // Initialize progress tracking
        activeDownloads[modelName] = LegacyDownloadProgress(
            modelName: modelName,
            status: "Checking for updates...",
            progress: 0.0
        )

        ollamaService.pullModel(
            modelName: modelName,
            onProgress: { progress in
                Task { @MainActor in
                    self.activeDownloads[modelName] = LegacyDownloadProgress(
                        modelName: modelName,
                        status: progress.message,
                        progress: self.estimateProgress(from: progress.status)
                    )
                }
            },
            onComplete: { result in
                Task { @MainActor in
                    switch result {
                    case .success:
                        logger.info("Update complete: \(modelName)")
                        self.activeDownloads.removeValue(forKey: modelName)

                        // Refresh local models list
                        await modelsStore.fetchModels()

                        // Clear enrichment cache to get fresh metadata
                        self.enrichmentService.clearCache(for: modelName)
                        self.enrichedModels.removeValue(forKey: modelName)

                        // Re-enrich the updated model
                        if let updatedModel = modelsStore.models.first(where: { $0.name == modelName }) {
                            let enriched = await self.enrichmentService.enrichModel(updatedModel)
                            self.enrichedModels[modelName] = enriched
                        }
                    case .failure(let error):
                        logger.error("Update failed: \(error.localizedDescription)")
                        self.activeDownloads[modelName] = LegacyDownloadProgress(
                            modelName: modelName,
                            status: "Error: \(error.localizedDescription)",
                            progress: 0.0,
                            error: error.localizedDescription
                        )
                    }
                }
            }
        )
    }

    // MARK: - Helper

    private func estimateProgress(from status: String) -> Double {
        switch status {
        case "starting": return 0.1
        case "downloading": return 0.5
        case "verifying": return 0.8
        case "completed": return 1.0
        default: return 0.5
        }
    }
}
