//
//  ModelDiscoveryWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Browse and download models from Ollama library
//  Refactored in Phase 6.22 - extracted panes and data manager
//

import SwiftUI

struct ModelDiscoveryWorkspace: View {
    @State private var selectedModel: LibraryModel? = nil

    // Search and filters
    @State private var searchText: String = ""
    @State private var selectedModelType: ModelTypeFilter = .all
    @State private var selectedCapability: CapabilityFilter = .all
    @State private var sortBy: SortOption = .pulls

    // Manager (Phase 6.22)
    @State private var dataManager = ModelDiscoveryDataManager()

    var body: some View {
        ThreePaneLayout {
            // Left Pane: Filters
            ModelDiscoveryFiltersPane(
                searchText: $searchText,
                selectedModelType: $selectedModelType,
                selectedCapability: $selectedCapability,
                sortBy: $sortBy,
                currentPage: dataManager.currentPage,
                totalCount: dataManager.totalCount,
                pageSize: dataManager.getPageSize(),
                isLoading: dataManager.isLoading,
                onSearch: {
                    await loadModels(reset: true)
                }
            )
        } middlePane: {
            // Middle Pane: Model List
            ModelDiscoveryListPane(
                libraryModels: dataManager.libraryModels,
                selectedModel: selectedModel,
                isLoading: dataManager.isLoading,
                error: dataManager.error,
                downloadingModel: dataManager.downloadingModel,
                currentPage: dataManager.currentPage,
                totalCount: dataManager.totalCount,
                pageSize: dataManager.getPageSize(),
                onSelectModel: { model in
                    selectedModel = model
                },
                onRetry: {
                    await loadModels()
                },
                onPreviousPage: {
                    dataManager.previousPage()
                    Task { await loadModels() }
                },
                onNextPage: {
                    dataManager.nextPage()
                    Task { await loadModels() }
                }
            )
        } rightPane: {
            // Right Pane: Model Detail
            ModelDiscoveryDetailPane(
                selectedModel: selectedModel,
                downloadingModel: dataManager.downloadingModel,
                downloadProgress: dataManager.downloadProgress,
                onDownload: { model in
                    await dataManager.downloadModel(model)
                }
            )
        }
        .task {
            await loadModels()
        }
    }

    // MARK: - Data Operations

    @MainActor
    private func loadModels(reset: Bool = false) async {
        await dataManager.loadModels(
            searchText: searchText,
            selectedModelType: selectedModelType,
            selectedCapability: selectedCapability,
            sortBy: sortBy,
            reset: reset
        )
    }
}

// Components and models extracted to:
// - ModelDiscovery/LibraryModelRow.swift (Phase 6.10)
// - ModelDiscovery/ModelDiscoveryModels.swift (Phase 6.10)
// - ModelDiscovery/ModelDiscoveryFiltersPane.swift (Phase 6.22)
// - ModelDiscovery/ModelDiscoveryListPane.swift (Phase 6.22)
// - ModelDiscovery/ModelDiscoveryDetailPane.swift (Phase 6.22)
// - ModelDiscovery/ModelDiscoveryDataManager.swift (Phase 6.22)

// MARK: - Preview

#Preview {
    ModelDiscoveryWorkspace()
        .frame(width: 1200, height: 800)
}
