//
//  ModelDiscoveryDataManager.swift
//  MagnetarStudio (macOS)
//
//  Data manager for model discovery - Extracted from ModelDiscoveryWorkspace.swift (Phase 6.22)
//

import SwiftUI

@MainActor
@Observable
class ModelDiscoveryDataManager {
    var libraryModels: [LibraryModel] = []
    var isLoading: Bool = false
    var error: String? = nil
    var currentPage: Int = 0
    var totalCount: Int = 0

    // Download state
    var downloadingModel: String? = nil
    var downloadProgress: String? = nil

    private let libraryService = ModelLibraryService.shared
    private let ollamaService = OllamaService.shared
    private let pageSize: Int = 20

    func loadModels(
        searchText: String,
        selectedModelType: ModelTypeFilter,
        selectedCapability: CapabilityFilter,
        sortBy: SortOption,
        reset: Bool = false
    ) async {
        if reset {
            currentPage = 0
        }

        isLoading = true
        error = nil

        do {
            let response = try await libraryService.browseLibrary(
                search: searchText.isEmpty ? nil : searchText,
                modelType: selectedModelType.apiValue,
                capability: selectedCapability.apiValue,
                sortBy: sortBy.apiValue,
                order: "desc",
                limit: pageSize,
                skip: currentPage * pageSize
            )

            libraryModels = response.models
            totalCount = response.totalCount
            isLoading = false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
        }
    }

    func downloadModel(_ model: LibraryModel) async {
        downloadingModel = model.modelIdentifier
        downloadProgress = "Starting download..."

        // Use the first tag as the model name to download
        let modelToDownload = model.tags.first ?? model.modelIdentifier

        ollamaService.pullModel(
            modelName: modelToDownload,
            onProgress: { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress.message
                }
            },
            onComplete: { [weak self] result in
                Task { @MainActor in
                    self?.downloadingModel = nil
                    self?.downloadProgress = nil

                    switch result {
                    case .success:
                        // Could show success message
                        break
                    case .failure(let error):
                        self?.error = error.localizedDescription
                    }
                }
            }
        )
    }

    func nextPage() {
        currentPage += 1
    }

    func previousPage() {
        currentPage -= 1
    }

    func getPageSize() -> Int {
        return pageSize
    }
}
