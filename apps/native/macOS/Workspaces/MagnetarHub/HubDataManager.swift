//
//  HubDataManager.swift
//  MagnetarStudio (macOS)
//
//  Data loading manager - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HubDataManager")

@MainActor
@Observable
class HubDataManager {
    var recommendedModels: [BackendRecommendedModel] = []
    var isLoadingRecommendations: Bool = false

    private let capabilityService = SystemCapabilityService.shared
    private let recommendationService = ModelRecommendationService.shared

    func loadInitialData(modelsStore: ModelsStore, ollamaService: OllamaService) async -> Bool {
        // Load local models
        await modelsStore.fetchModels()
        let ollamaRunning = await ollamaService.checkStatus()

        // Load recommended models from backend
        await loadRecommendations(installedModels: modelsStore.models.map { $0.name })

        return ollamaRunning
    }

    func loadRecommendations(installedModels: [String]) async {
        isLoadingRecommendations = true

        do {
            let response = try await recommendationService.getRecommendations(
                totalMemoryGB: capabilityService.totalMemoryGB,
                cpuCores: capabilityService.cpuCores,
                hasMetal: capabilityService.hasMetalSupport,
                installedModels: installedModels
            )

            recommendedModels = response.recommendations
            logger.info("Loaded \(response.totalCount) recommended models from backend")
        } catch {
            logger.error("Failed to load recommendations: \(error)")
            // Keep empty list on error
        }

        isLoadingRecommendations = false
    }
}
