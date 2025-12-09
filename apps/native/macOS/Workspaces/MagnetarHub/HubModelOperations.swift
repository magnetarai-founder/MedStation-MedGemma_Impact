//
//  HubModelOperations.swift
//  MagnetarStudio (macOS)
//
//  Model operations manager - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI

@MainActor
@Observable
class HubModelOperations {
    var activeDownloads: [String: DownloadProgress] = [:]
    var enrichedModels: [String: EnrichedModelMetadata] = [:]
    var isEnrichingModels: Bool = false

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
            print("❌ Cannot download - Ollama server not running")
            return
        }

        guard networkConnected else {
            print("❌ Cannot download - No internet connection")
            return
        }

        // Initialize progress tracking
        activeDownloads[modelName] = DownloadProgress(
            modelName: modelName,
            status: "Starting download...",
            progress: 0.0
        )

        print("📥 Starting download: \(modelName)")

        ollamaService.pullModel(
            modelName: modelName,
            onProgress: { progress in
                Task { @MainActor in
                    self.activeDownloads[modelName] = DownloadProgress(
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
                        print("✅ Download complete: \(modelName)")
                        self.activeDownloads.removeValue(forKey: modelName)
                        // Refresh local models list
                        await onRefreshModels()
                    case .failure(let error):
                        print("❌ Download failed: \(error.localizedDescription)")
                        self.activeDownloads[modelName] = DownloadProgress(
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
        Task {
            do {
                print("🗑️ Deleting model: \(modelName)")
                let result = try await ollamaService.removeModel(modelName: modelName)
                print("✅ \(result.message)")

                // Refresh local models list
                await onRefreshModels()

                // Clear enrichment cache for this model
                enrichmentService.clearCache(for: modelName)
                enrichedModels.removeValue(forKey: modelName)

                // Close modal
                onCloseModal()
            } catch {
                print("❌ Failed to delete model: \(error.localizedDescription)")
            }
        }
    }

    func updateModel(_ modelName: String, ollamaRunning: Bool, networkConnected: Bool, modelsStore: ModelsStore) {
        guard ollamaRunning else {
            print("❌ Cannot update - Ollama server not running")
            return
        }

        guard networkConnected else {
            print("❌ Cannot update - No internet connection")
            return
        }

        // Re-pull the model to update it
        print("🔄 Updating model: \(modelName)")

        // Initialize progress tracking
        activeDownloads[modelName] = DownloadProgress(
            modelName: modelName,
            status: "Checking for updates...",
            progress: 0.0
        )

        ollamaService.pullModel(
            modelName: modelName,
            onProgress: { progress in
                Task { @MainActor in
                    self.activeDownloads[modelName] = DownloadProgress(
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
                        print("✅ Update complete: \(modelName)")
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
                        print("❌ Update failed: \(error.localizedDescription)")
                        self.activeDownloads[modelName] = DownloadProgress(
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
