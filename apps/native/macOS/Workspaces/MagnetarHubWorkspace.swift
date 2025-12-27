//
//  MagnetarHubWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Clean two-pane model management: categories + card grid + modal details
//  Refactored in Phase 6.19 - extracted managers for data, network, Ollama, cloud, and operations
//

import SwiftUI

struct MagnetarHubWorkspace: View {
    @State private var selectedCategory: HubCategory = .myModels
    @State private var selectedModel: AnyModelItem? = nil
    @State private var showModelDetail: Bool = false
    // Note: showLibraryBrowser removed - ModelDiscoveryWorkspace not in project
    // Users can browse via Safari button in HubDiscoverToolbar

    // Managers (Phase 6.19)
    @State private var dataManager = HubDataManager()
    @State private var networkManager = HubNetworkManager()
    @State private var ollamaManager = HubOllamaManager()
    @State private var cloudManager = HubCloudManager()
    @State private var modelOperations = HubModelOperations()

    // Local models store
    @State private var modelsStore = ModelsStore()

    private let capabilityService = SystemCapabilityService.shared

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
            networkManager.startNetworkMonitoring()
        }
        .sheet(isPresented: $showModelDetail) {
            if let model = selectedModel {
                ModelDetailModal(
                    model: model,
                    enrichedMetadata: modelOperations.enrichedModels,
                    activeDownloads: $modelOperations.activeDownloads,
                    onDownload: { modelName in
                        modelOperations.downloadModel(
                            modelName: modelName,
                            ollamaRunning: ollamaManager.ollamaServerRunning,
                            networkConnected: networkManager.isNetworkConnected,
                            onRefreshModels: {
                                await modelsStore.fetchModels()
                            }
                        )
                    },
                    onDelete: { modelName in
                        modelOperations.deleteModel(
                            modelName,
                            onRefreshModels: {
                                await modelsStore.fetchModels()
                            },
                            onCloseModal: {
                                showModelDetail = false
                                selectedModel = nil
                            }
                        )
                    },
                    onUpdate: { modelName in
                        modelOperations.updateModel(
                            modelName,
                            ollamaRunning: ollamaManager.ollamaServerRunning,
                            networkConnected: networkManager.isNetworkConnected,
                            modelsStore: modelsStore
                        )
                    }
                )
            }
        }
    }

    // MARK: - Categories Pane

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
                    isRunning: ollamaManager.ollamaServerRunning,
                    isActionInProgress: ollamaManager.isOllamaActionInProgress,
                    onToggle: {
                        Task { await ollamaManager.toggleOllama() }
                    },
                    onRestart: {
                        Task { await ollamaManager.restartOllama() }
                    }
                )

                HubCloudStatus(
                    isAuthenticated: cloudManager.isCloudAuthenticated,
                    isActionInProgress: cloudManager.isCloudActionInProgress,
                    username: cloudManager.cloudUsername,
                    onConnect: {
                        Task { await cloudManager.connectCloud() }
                    },
                    onDisconnect: {
                        Task { await cloudManager.disconnectCloud() }
                    },
                    onReconnect: {
                        Task { await cloudManager.reconnectCloud() }
                    },
                    isSyncing: cloudManager.isSyncing,
                    pendingChanges: cloudManager.pendingSyncChanges,
                    activeConflicts: cloudManager.activeConflicts,
                    onSync: {
                        Task { await cloudManager.triggerSync() }
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
                    isNetworkConnected: networkManager.isNetworkConnected,
                    onBrowseModels: networkManager.openOllamaWebsite
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
                                downloadProgress: modelOperations.activeDownloads[model.name],
                                onDownload: {
                                    modelOperations.downloadModel(
                                        modelName: model.name,
                                        ollamaRunning: ollamaManager.ollamaServerRunning,
                                        networkConnected: networkManager.isNetworkConnected,
                                        onRefreshModels: {
                                            await modelsStore.fetchModels()
                                        }
                                    )
                                },
                                enrichedMetadata: modelOperations.enrichedModels
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                Task {
                                    await modelOperations.handleModelTap(model)
                                    selectedModel = model
                                    showModelDetail = true
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
        let ollamaRunning = await dataManager.loadInitialData(
            modelsStore: modelsStore,
            ollamaService: OllamaService.shared
        )
        ollamaManager.ollamaServerRunning = ollamaRunning

        // Refresh cloud sync status if authenticated
        if cloudManager.isCloudAuthenticated {
            await cloudManager.refreshSyncStatus()
            // Start auto-sync (5 minute interval)
            cloudManager.startAutoSync(intervalSeconds: 300)
        }
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
            return dataManager.recommendedModels.map { AnyModelItem.backendRecommended($0) }
        case .cloud:
            return cloudManager.cloudModels.map { AnyModelItem.cloud($0) }
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
