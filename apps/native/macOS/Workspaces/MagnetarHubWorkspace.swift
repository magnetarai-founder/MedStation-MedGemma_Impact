//
//  MagnetarHubWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Clean two-pane model management: categories + card grid + modal details
//

import SwiftUI
import Network

struct MagnetarHubWorkspace: View {
    @State private var selectedCategory: HubCategory = .myModels
    @State private var selectedModel: AnyModelItem? = nil
    @State private var showModelDetail: Bool = false

    // Local models
    @State private var modelsStore = ModelsStore()
    @State private var ollamaServerRunning: Bool = false
    @State private var isOllamaActionInProgress: Bool = false

    // Discovery - Now using backend recommendations
    @State private var isNetworkConnected: Bool = false
    @State private var recommendedModels: [BackendRecommendedModel] = []
    @State private var isLoadingRecommendations: Bool = false

    // Cloud models
    @State private var cloudModels: [OllamaModel] = []
    @State private var isCloudAuthenticated: Bool = false
    @State private var isLoadingCloud: Bool = false
    @State private var isCloudActionInProgress: Bool = false
    @State private var cloudUsername: String? = nil

    // Download tracking
    @State private var activeDownloads: [String: DownloadProgress] = [:]

    // Model enrichment (for My Models)
    @State private var enrichedModels: [String: EnrichedModelMetadata] = [:]
    @State private var isEnrichingModels: Bool = false

    private let ollamaService = OllamaService.shared
    private let capabilityService = SystemCapabilityService.shared
    private let recommendationService = ModelRecommendationService.shared
    private let enrichmentService = ModelEnrichmentService.shared
    private let networkMonitor = NWPathMonitor()

    var body: some View {
        HStack(spacing: 0) {
            // Left: Categories
            categoriesPane
                .frame(width: 220)

            Divider()

            // Right: Model Cards
            cardsPane
        }
        .task {
            await loadInitialData()
            startNetworkMonitoring()
        }
        .sheet(isPresented: $showModelDetail) {
            if let model = selectedModel {
                ModelDetailModal(
                    model: model,
                    enrichedMetadata: enrichedModels,
                    activeDownloads: $activeDownloads,
                    onDownload: downloadModel,
                    onDelete: deleteModel,
                    onUpdate: updateModel
                )
            }
        }
    }

    // MARK: - Categories Pane
    // Components extracted to focused modules (Phase 6.12)

    private var categoriesPane: some View {
        VStack(spacing: 0) {
            // Header with System Badge
            HubCategoriesHeader(
                systemBadgeText: systemBadgeText,
                systemBadgeColor: systemBadgeColor
            )

            Divider()

            // Categories
            List(HubCategory.allCases, selection: $selectedCategory) { category in
                CategoryRow(category: category)
                    .tag(category)
            }
            .listStyle(.sidebar)

            Divider()

            // Ollama Server Status & MagnetarCloud Status
            VStack(spacing: 12) {
                HubOllamaStatus(
                    isRunning: ollamaServerRunning,
                    isActionInProgress: isOllamaActionInProgress,
                    onToggle: {
                        Task { await toggleOllama() }
                    },
                    onRestart: {
                        Task { await restartOllama() }
                    }
                )

                HubCloudStatus(
                    isAuthenticated: isCloudAuthenticated,
                    isActionInProgress: isCloudActionInProgress,
                    username: cloudUsername,
                    onConnect: {
                        Task { await connectCloud() }
                    },
                    onDisconnect: {
                        Task { await disconnectCloud() }
                    },
                    onReconnect: {
                        Task { await reconnectCloud() }
                    }
                )
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Cards Pane

    private var cardsPane: some View {
        VStack(spacing: 0) {
            // Toolbar (for Discover category)
            if selectedCategory == .discover {
                HubDiscoverToolbar(
                    isNetworkConnected: isNetworkConnected,
                    onBrowseModels: openOllamaWebsite
                )
                Divider()
            }

            // Cards grid
            ScrollView {
                if displayedModels.isEmpty {
                    HubEmptyState(category: selectedCategory)
                } else {
                    LazyVGrid(columns: gridColumns, spacing: 20) {
                        ForEach(displayedModels) { model in
                            ModelCard(
                                model: model,
                                downloadProgress: activeDownloads[model.name],
                                onDownload: {
                                    downloadModel(modelName: model.name)
                                },
                                enrichedMetadata: enrichedModels
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                Task {
                                    await handleModelTap(model)
                                }
                            }
                        }
                    }
                    .padding(20)
                }
            }
        }
    }

    // MARK: - Data Loading

    private func loadInitialData() async {
        // Load local models
        await modelsStore.fetchModels()
        ollamaServerRunning = await ollamaService.checkStatus()

        // Load recommended models from backend
        await loadRecommendations()

        // Load cloud auth status
        // TODO: Add cloud auth check
    }

    private func loadRecommendations() async {
        isLoadingRecommendations = true

        do {
            let response = try await recommendationService.getRecommendations(
                totalMemoryGB: capabilityService.totalMemoryGB,
                cpuCores: capabilityService.cpuCores,
                hasMetal: capabilityService.hasMetalSupport,
                installedModels: modelsStore.models.map { $0.name }
            )

            recommendedModels = response.recommendations
            print("✅ Loaded \(response.totalCount) recommended models from backend")
        } catch {
            print("❌ Failed to load recommendations: \(error)")
            // Keep empty list on error
        }

        isLoadingRecommendations = false
    }

    // MARK: - Model Interaction

    private func handleModelTap(_ model: AnyModelItem) async {
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

        // Show modal
        selectedModel = model
        showModelDetail = true
    }

    // MARK: - Network Monitoring

    private func startNetworkMonitoring() {
        let queue = DispatchQueue(label: "NetworkMonitor")
        networkMonitor.pathUpdateHandler = { path in
            DispatchQueue.main.async {
                self.isNetworkConnected = path.status == .satisfied
            }
        }
        networkMonitor.start(queue: queue)
    }

    private func openOllamaWebsite() {
        if let url = URL(string: "https://ollama.com/library") {
            NSWorkspace.shared.open(url)
        }
    }

    // MARK: - Ollama Management

    private func toggleOllama() async {
        isOllamaActionInProgress = true

        do {
            if ollamaServerRunning {
                // Stop Ollama
                try await ollamaService.stop()
                await MainActor.run {
                    ollamaServerRunning = false
                }
            } else {
                // Start Ollama
                try await ollamaService.start()
                await MainActor.run {
                    ollamaServerRunning = true
                }
            }
        } catch {
            print("Failed to toggle Ollama: \(error)")
        }

        isOllamaActionInProgress = false
    }

    private func restartOllama() async {
        isOllamaActionInProgress = true

        do {
            try await ollamaService.restart()
            await MainActor.run {
                ollamaServerRunning = true
            }
        } catch {
            print("Failed to restart Ollama: \(error)")
            await MainActor.run {
                ollamaServerRunning = false
            }
        }

        isOllamaActionInProgress = false
    }

    // MARK: - Cloud Management

    private func connectCloud() async {
        isCloudActionInProgress = true

        // TODO: Implement MagnetarCloud authentication
        // For now, simulate connection
        try? await Task.sleep(nanoseconds: 1_000_000_000)

        await MainActor.run {
            isCloudAuthenticated = true
            cloudUsername = "User"
            isCloudActionInProgress = false
        }
    }

    private func disconnectCloud() async {
        isCloudActionInProgress = true

        // TODO: Implement MagnetarCloud disconnection
        try? await Task.sleep(nanoseconds: 500_000_000)

        await MainActor.run {
            isCloudAuthenticated = false
            cloudUsername = nil
            cloudModels = []
            isCloudActionInProgress = false
        }
    }

    private func reconnectCloud() async {
        isCloudActionInProgress = true

        // TODO: Implement MagnetarCloud reconnection
        try? await Task.sleep(nanoseconds: 1_000_000_000)

        await MainActor.run {
            isCloudActionInProgress = false
        }
    }

    // MARK: - Model Downloads

    private func downloadModel(modelName: String) {
        guard ollamaServerRunning else {
            print("❌ Cannot download - Ollama server not running")
            return
        }

        guard isNetworkConnected else {
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
                        await self.modelsStore.fetchModels()
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

    private func estimateProgress(from status: String) -> Double {
        switch status {
        case "starting": return 0.1
        case "downloading": return 0.5
        case "verifying": return 0.8
        case "completed": return 1.0
        default: return 0.5
        }
    }

    private func deleteModel(_ modelName: String) {
        Task {
            do {
                print("🗑️ Deleting model: \(modelName)")
                let result = try await ollamaService.removeModel(modelName: modelName)
                print("✅ \(result.message)")

                // Refresh local models list
                await modelsStore.fetchModels()

                // Clear enrichment cache for this model
                enrichmentService.clearCache(for: modelName)
                enrichedModels.removeValue(forKey: modelName)

                // Close modal
                showModelDetail = false
                selectedModel = nil
            } catch {
                print("❌ Failed to delete model: \(error.localizedDescription)")
            }
        }
    }

    private func updateModel(_ modelName: String) {
        guard ollamaServerRunning else {
            print("❌ Cannot update - Ollama server not running")
            return
        }

        guard isNetworkConnected else {
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
                        await self.modelsStore.fetchModels()

                        // Clear enrichment cache to get fresh metadata
                        self.enrichmentService.clearCache(for: modelName)
                        self.enrichedModels.removeValue(forKey: modelName)

                        // Re-enrich the updated model
                        if let updatedModel = self.modelsStore.models.first(where: { $0.name == modelName }) {
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

    // MARK: - Computed Properties

    private var gridColumns: [GridItem] {
        [
            GridItem(.adaptive(minimum: 280, maximum: 320), spacing: 20)
        ]
    }

    private var displayedModels: [AnyModelItem] {
        switch selectedCategory {
        case .myModels:
            return modelsStore.models.map { AnyModelItem.local($0) }
        case .discover:
            return recommendedModels.map { AnyModelItem.backendRecommended($0) }
        case .cloud:
            return cloudModels.map { AnyModelItem.cloud($0) }
        }
    }

    private var systemBadgeText: String {
        let memoryGB = Int(capabilityService.totalMemoryGB)
        if memoryGB >= 64 {
            return "\(memoryGB)GB • High-End"
        } else if memoryGB >= 32 {
            return "\(memoryGB)GB • Great"
        } else if memoryGB >= 16 {
            return "\(memoryGB)GB • Good"
        } else {
            return "\(memoryGB)GB • Entry"
        }
    }

    private var systemBadgeColor: Color {
        let memoryGB = Int(capabilityService.totalMemoryGB)
        if memoryGB >= 64 {
            return .green
        } else if memoryGB >= 32 {
            return .blue
        } else if memoryGB >= 16 {
            return .cyan
        } else {
            return .orange
        }
    }

}


// MARK: - Preview

#Preview {
    MagnetarHubWorkspace()
        .frame(width: 1200, height: 800)
}
