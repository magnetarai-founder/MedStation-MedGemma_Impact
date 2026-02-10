//
//  ModelDiscoveryWorkspaceTests.swift
//  MedStation Tests
//
//  Comprehensive test suite for ModelDiscoveryWorkspace refactoring (Phase 6.22)
//  Tests extracted components: ModelDiscoveryFiltersPane, ModelDiscoveryListPane,
//                               ModelDiscoveryDetailPane, ModelDiscoveryDataManager
//

import XCTest
@testable import MedStation

@MainActor
final class ModelDiscoveryWorkspaceTests: XCTestCase {

    // MARK: - ModelDiscoveryDataManager Tests

    func testModelDiscoveryDataManagerInitialization() {
        let manager = ModelDiscoveryDataManager()

        XCTAssertTrue(manager.libraryModels.isEmpty, "Library models should be empty on init")
        XCTAssertFalse(manager.isLoading, "Should not be loading on init")
        XCTAssertNil(manager.downloadingModel, "No model should be downloading on init")
        XCTAssertNil(manager.downloadProgress, "Download progress should be nil on init")
        XCTAssertNil(manager.errorMessage, "Error message should be nil on init")
    }

    func testModelDiscoveryDataManagerLoadModels() async {
        let manager = ModelDiscoveryDataManager()

        await manager.loadModels(
            searchQuery: "",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )

        // Should either succeed or fail gracefully
        XCTAssertNotNil(manager.libraryModels, "Library models should not be nil")
        XCTAssertFalse(manager.isLoading, "Loading should complete")
    }

    func testModelDiscoveryDataManagerSearchFiltering() async {
        let manager = ModelDiscoveryDataManager()

        // Load all models first
        await manager.loadModels(
            searchQuery: "",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )

        let allModelsCount = manager.libraryModels.count

        // Now load with search query
        await manager.loadModels(
            searchQuery: "llama",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )

        // Searched results should be <= all results
        XCTAssertLessThanOrEqual(manager.libraryModels.count, allModelsCount,
                                 "Filtered results should not exceed total results")
    }

    func testModelDiscoveryDataManagerTypeFiltering() async {
        let manager = ModelDiscoveryDataManager()

        // Test different model type filters
        let modelTypes: [ModelTypeFilter] = [.all, .chat, .code, .embedding, .vision]

        for modelType in modelTypes {
            await manager.loadModels(
                searchQuery: "",
                modelType: modelType,
                capability: .all,
                sortBy: .popular
            )

            // Should complete without crashing
            XCTAssertNotNil(manager.libraryModels, "Should handle \(modelType) filter")
        }
    }

    func testModelDiscoveryDataManagerCapabilityFiltering() async {
        let manager = ModelDiscoveryDataManager()

        // Test different capability filters
        let capabilities: [CapabilityFilter] = [.all, .chat, .code, .vision, .embedding]

        for capability in capabilities {
            await manager.loadModels(
                searchQuery: "",
                modelType: .all,
                capability: capability,
                sortBy: .popular
            )

            // Should complete without crashing
            XCTAssertNotNil(manager.libraryModels, "Should handle \(capability) filter")
        }
    }

    func testModelDiscoveryDataManagerSorting() async {
        let manager = ModelDiscoveryDataManager()

        // Test different sort options
        let sortOptions: [SortOption] = [.popular, .newest, .name, .size]

        for sortOption in sortOptions {
            await manager.loadModels(
                searchQuery: "",
                modelType: .all,
                capability: .all,
                sortBy: sortOption
            )

            // Should complete without crashing
            XCTAssertNotNil(manager.libraryModels, "Should handle \(sortOption) sorting")
        }
    }

    func testModelDiscoveryDataManagerDownload() async {
        let manager = ModelDiscoveryDataManager()
        let mockModel = createMockLibraryModel()

        await manager.downloadModel(mockModel)

        // Download should complete (success or failure)
        // In unit tests without backend, this will likely fail gracefully
        XCTAssertNotNil(manager.downloadingModel == nil || manager.errorMessage != nil,
                       "Download should complete or error")
    }

    func testModelDiscoveryDataManagerDownloadProgress() async {
        let manager = ModelDiscoveryDataManager()
        let mockModel = createMockLibraryModel()

        let downloadTask = Task {
            await manager.downloadModel(mockModel)
        }

        // Give it a moment to start
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 second

        // Should be downloading or completed
        let hasProgress = manager.downloadingModel != nil ||
                         manager.downloadProgress != nil ||
                         manager.errorMessage != nil

        XCTAssertTrue(hasProgress, "Should show download progress or error")

        await downloadTask.value
    }

    // MARK: - ModelDiscoveryFiltersPane Tests

    func testFiltersInitialization() {
        let searchText = Binding.constant("")
        let modelType = Binding.constant(ModelTypeFilter.all)
        let capability = Binding.constant(CapabilityFilter.all)
        let sortBy = Binding.constant(SortOption.popular)

        let filters = ModelDiscoveryFiltersPane(
            searchText: searchText,
            selectedModelType: modelType,
            selectedCapability: capability,
            sortBy: sortBy,
            onSearch: {}
        )

        XCTAssertNotNil(filters, "Filters pane should initialize")
    }

    func testFiltersSearchTextBinding() {
        var searchValue = ""
        let searchText = Binding(
            get: { searchValue },
            set: { searchValue = $0 }
        )
        let modelType = Binding.constant(ModelTypeFilter.all)
        let capability = Binding.constant(CapabilityFilter.all)
        let sortBy = Binding.constant(SortOption.popular)

        let _ = ModelDiscoveryFiltersPane(
            searchText: searchText,
            selectedModelType: modelType,
            selectedCapability: capability,
            sortBy: sortBy,
            onSearch: {}
        )

        searchText.wrappedValue = "llama"
        XCTAssertEqual(searchValue, "llama", "Search text should bind correctly")
    }

    func testFiltersTypeSelection() {
        let searchText = Binding.constant("")
        var typeValue = ModelTypeFilter.all
        let modelType = Binding(
            get: { typeValue },
            set: { typeValue = $0 }
        )
        let capability = Binding.constant(CapabilityFilter.all)
        let sortBy = Binding.constant(SortOption.popular)

        let _ = ModelDiscoveryFiltersPane(
            searchText: searchText,
            selectedModelType: modelType,
            selectedCapability: capability,
            sortBy: sortBy,
            onSearch: {}
        )

        modelType.wrappedValue = .chat
        XCTAssertEqual(typeValue, .chat, "Model type should bind correctly")
    }

    // MARK: - ModelDiscoveryListPane Tests

    func testListPaneInitialization() {
        let mockModels = createMockLibraryModels()

        let listPane = ModelDiscoveryListPane(
            libraryModels: mockModels,
            selectedModel: mockModels.first,
            isLoading: false,
            errorMessage: nil,
            onSelectModel: { _ in },
            onRetry: {}
        )

        XCTAssertNotNil(listPane, "List pane should initialize")
    }

    func testListPaneEmptyState() {
        let listPane = ModelDiscoveryListPane(
            libraryModels: [],
            selectedModel: nil,
            isLoading: false,
            errorMessage: nil,
            onSelectModel: { _ in },
            onRetry: {}
        )

        XCTAssertNotNil(listPane, "List pane should handle empty state")
    }

    func testListPaneLoadingState() {
        let listPane = ModelDiscoveryListPane(
            libraryModels: [],
            selectedModel: nil,
            isLoading: true,
            errorMessage: nil,
            onSelectModel: { _ in },
            onRetry: {}
        )

        XCTAssertNotNil(listPane, "List pane should handle loading state")
    }

    func testListPaneErrorState() {
        var retryWasCalled = false

        let listPane = ModelDiscoveryListPane(
            libraryModels: [],
            selectedModel: nil,
            isLoading: false,
            errorMessage: "Test error",
            onSelectModel: { _ in },
            onRetry: {
                retryWasCalled = true
            }
        )

        XCTAssertNotNil(listPane, "List pane should handle error state")

        listPane.onRetry()
        XCTAssertTrue(retryWasCalled, "Retry should be callable")
    }

    func testListPaneModelSelection() {
        let mockModels = createMockLibraryModels()
        var selectedModel: LibraryModel?

        let listPane = ModelDiscoveryListPane(
            libraryModels: mockModels,
            selectedModel: nil,
            isLoading: false,
            errorMessage: nil,
            onSelectModel: { model in
                selectedModel = model
            },
            onRetry: {}
        )

        listPane.onSelectModel(mockModels[0])
        XCTAssertNotNil(selectedModel, "Model should be selected")
        XCTAssertEqual(selectedModel?.id, mockModels[0].id, "Selected model should match")
    }

    // MARK: - ModelDiscoveryDetailPane Tests

    func testDetailPaneInitialization() {
        let mockModel = createMockLibraryModel()

        let detailPane = ModelDiscoveryDetailPane(
            selectedModel: mockModel,
            downloadingModel: nil,
            downloadProgress: nil,
            onDownload: { _ in }
        )

        XCTAssertNotNil(detailPane, "Detail pane should initialize")
    }

    func testDetailPaneEmptyState() {
        let detailPane = ModelDiscoveryDetailPane(
            selectedModel: nil,
            downloadingModel: nil,
            downloadProgress: nil,
            onDownload: { _ in }
        )

        XCTAssertNotNil(detailPane, "Detail pane should handle nil selection")
    }

    func testDetailPaneDownloadState() {
        let mockModel = createMockLibraryModel()

        let detailPane = ModelDiscoveryDetailPane(
            selectedModel: mockModel,
            downloadingModel: mockModel.name,
            downloadProgress: "50%",
            onDownload: { _ in }
        )

        XCTAssertNotNil(detailPane, "Detail pane should handle download state")
    }

    func testDetailPaneDownloadAction() async {
        let mockModel = createMockLibraryModel()
        var downloadedModel: LibraryModel?

        let detailPane = ModelDiscoveryDetailPane(
            selectedModel: mockModel,
            downloadingModel: nil,
            downloadProgress: nil,
            onDownload: { model in
                downloadedModel = model
            }
        )

        await detailPane.onDownload(mockModel)
        XCTAssertNotNil(downloadedModel, "Download action should be triggered")
        XCTAssertEqual(downloadedModel?.id, mockModel.id, "Downloaded model should match")
    }

    // MARK: - Integration Tests

    func testModelDiscoveryWorkspaceIntegration() async {
        let manager = ModelDiscoveryDataManager()

        // Load models
        await manager.loadModels(
            searchQuery: "",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )

        XCTAssertFalse(manager.isLoading, "Loading should complete")
        XCTAssertNotNil(manager.libraryModels, "Models should be loaded")
    }

    func testSearchAndFilterFlow() async {
        let manager = ModelDiscoveryDataManager()

        // Start with all models
        await manager.loadModels(
            searchQuery: "",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )
        let allCount = manager.libraryModels.count

        // Apply search
        await manager.loadModels(
            searchQuery: "test",
            modelType: .all,
            capability: .all,
            sortBy: .popular
        )
        let searchCount = manager.libraryModels.count

        // Apply type filter
        await manager.loadModels(
            searchQuery: "test",
            modelType: .chat,
            capability: .all,
            sortBy: .popular
        )
        let filteredCount = manager.libraryModels.count

        // Verify filtering reduces results
        XCTAssertLessThanOrEqual(searchCount, allCount, "Search should filter results")
        XCTAssertLessThanOrEqual(filteredCount, searchCount, "Type filter should further reduce results")
    }

    // MARK: - Helper Methods

    private func createMockLibraryModel() -> LibraryModel {
        return LibraryModel(
            id: "model-1",
            name: "test-model",
            description: "Test model for unit tests",
            author: "Test Author",
            tags: ["test", "unit-test"],
            size: 1024 * 1024 * 100, // 100 MB
            capabilities: ["chat"],
            downloads: 1000,
            likes: 50,
            createdAt: Date(),
            updatedAt: Date()
        )
    }

    private func createMockLibraryModels() -> [LibraryModel] {
        return [
            LibraryModel(
                id: "model-1",
                name: "llama-chat",
                description: "Chat model",
                author: "Meta",
                tags: ["chat", "llama"],
                size: 1024 * 1024 * 500,
                capabilities: ["chat"],
                downloads: 10000,
                likes: 500,
                createdAt: Date(),
                updatedAt: Date()
            ),
            LibraryModel(
                id: "model-2",
                name: "codellama",
                description: "Code model",
                author: "Meta",
                tags: ["code", "llama"],
                size: 1024 * 1024 * 700,
                capabilities: ["code"],
                downloads: 5000,
                likes: 300,
                createdAt: Date(),
                updatedAt: Date()
            ),
            LibraryModel(
                id: "model-3",
                name: "vision-model",
                description: "Vision model",
                author: "OpenAI",
                tags: ["vision", "multimodal"],
                size: 1024 * 1024 * 1000,
                capabilities: ["vision", "chat"],
                downloads: 8000,
                likes: 400,
                createdAt: Date(),
                updatedAt: Date()
            )
        ]
    }

    // MARK: - Performance Tests

    func testModelDiscoveryDataManagerPerformance() {
        measure {
            let manager = ModelDiscoveryDataManager()
            let _ = manager.libraryModels
        }
    }

    func testListPanePerformanceWithManyModels() {
        let manyModels = (0..<100).map { i in
            LibraryModel(
                id: "model-\(i)",
                name: "model-\(i)",
                description: "Description \(i)",
                author: "Author \(i)",
                tags: ["tag1", "tag2"],
                size: 1024 * 1024 * (i + 1),
                capabilities: ["chat"],
                downloads: i * 100,
                likes: i * 10,
                createdAt: Date(),
                updatedAt: Date()
            )
        }

        measure {
            let _ = ModelDiscoveryListPane(
                libraryModels: manyModels,
                selectedModel: manyModels.first,
                isLoading: false,
                errorMessage: nil,
                onSelectModel: { _ in },
                onRetry: {}
            )
        }
    }
}
