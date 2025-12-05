//
//  ModelDiscoveryWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Browse and download models from Ollama library
//

import SwiftUI

struct ModelDiscoveryWorkspace: View {
    @State private var libraryModels: [LibraryModel] = []
    @State private var selectedModel: LibraryModel? = nil
    @State private var isLoading: Bool = false
    @State private var error: String? = nil

    // Search and filters
    @State private var searchText: String = ""
    @State private var selectedModelType: ModelTypeFilter = .all
    @State private var selectedCapability: CapabilityFilter = .all
    @State private var sortBy: SortOption = .pulls

    // Pagination
    @State private var currentPage: Int = 0
    @State private var totalCount: Int = 0
    private let pageSize: Int = 20

    // Download state
    @State private var downloadingModel: String? = nil
    @State private var downloadProgress: String? = nil

    private let libraryService = ModelLibraryService.shared
    private let ollamaService = OllamaService.shared

    var body: some View {
        ThreePaneLayout {
            // Left Pane: Filters
            filtersPane
        } middlePane: {
            // Middle Pane: Model List
            modelListPane
        } rightPane: {
            // Right Pane: Model Detail
            modelDetailPane
        }
        .task {
            await loadModels()
        }
    }

    // MARK: - Left Pane: Filters

    private var filtersPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Discover",
                icon: "magnifyingglass"
            )

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Search
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Search")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        TextField("Search models...", text: $searchText)
                            .textFieldStyle(.roundedBorder)
                            .onSubmit {
                                Task { await loadModels(reset: true) }
                            }

                        Button("Search") {
                            Task { await loadModels(reset: true) }
                        }
                        .buttonStyle(.bordered)
                        .disabled(isLoading)
                    }

                    Divider()

                    // Model Type
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Type")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        Picker("", selection: $selectedModelType) {
                            ForEach(ModelTypeFilter.allCases, id: \.self) { type in
                                Text(type.displayName).tag(type)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: selectedModelType) { _, _ in
                            Task { await loadModels(reset: true) }
                        }
                    }

                    Divider()

                    // Capability
                    VStack(alignment: \.leading, spacing: 8) {
                        Text("Capability")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        Picker("", selection: $selectedCapability) {
                            ForEach(CapabilityFilter.allCases, id: \.self) { cap in
                                Text(cap.displayName).tag(cap)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: selectedCapability) { _, _ in
                            Task { await loadModels(reset: true) }
                        }
                    }

                    Divider()

                    // Sort
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Sort By")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        Picker("", selection: $sortBy) {
                            ForEach(SortOption.allCases, id: \.self) { option in
                                Text(option.displayName).tag(option)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: sortBy) { _, _ in
                            Task { await loadModels(reset: true) }
                        }
                    }

                    Divider()

                    // Results info
                    if totalCount > 0 {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("\(totalCount) models found")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Text("Page \(currentPage + 1) of \((totalCount + pageSize - 1) / pageSize)")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding()
            }
        }
    }

    // MARK: - Middle Pane: Model List

    private var modelListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Models",
                icon: "square.stack.3d.up"
            )

            Divider()

            if isLoading && libraryModels.isEmpty {
                PaneLoadingState(message: "Loading models...")
            } else if let error = error {
                PaneErrorState(
                    icon: "exclamationmark.triangle",
                    title: "Failed to load models",
                    subtitle: error
                ) {
                    Button("Try Again") {
                        Task { await loadModels() }
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else if libraryModels.isEmpty {
                PaneEmptyState(
                    icon: "magnifyingglass",
                    title: "No models found",
                    subtitle: "Try adjusting your search or filters"
                )
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(libraryModels) { model in
                            LibraryModelRow(
                                model: model,
                                isSelected: selectedModel?.id == model.id,
                                isDownloading: downloadingModel == model.modelIdentifier
                            )
                            .onTapGesture {
                                selectedModel = model
                            }
                        }
                    }
                }

                // Pagination
                if totalCount > pageSize {
                    Divider()

                    HStack(spacing: 12) {
                        Button {
                            currentPage -= 1
                            Task { await loadModels() }
                        } label: {
                            Image(systemName: "chevron.left")
                        }
                        .disabled(currentPage == 0 || isLoading)

                        Text("Page \(currentPage + 1)")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Button {
                            currentPage += 1
                            Task { await loadModels() }
                        } label: {
                            Image(systemName: "chevron.right")
                        }
                        .disabled(currentPage >= (totalCount / pageSize) || isLoading)
                    }
                    .padding()
                }
            }
        }
    }

    // MARK: - Right Pane: Model Detail

    private var modelDetailPane: some View {
        Group {
            if let model = selectedModel {
                VStack(spacing: 0) {
                    // Model header
                    HStack(spacing: 16) {
                        Image(systemName: model.isOfficial ? "checkmark.seal.fill" : "cube.box.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(
                                model.isOfficial
                                    ? LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
                                    : LinearGradient.magnetarGradient
                            )

                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                Text(model.modelName)
                                    .font(.title2)
                                    .fontWeight(.bold)

                                if model.isOfficial {
                                    Text("OFFICIAL")
                                        .font(.caption2)
                                        .fontWeight(.bold)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.blue.opacity(0.2))
                                        .foregroundColor(.blue)
                                        .cornerRadius(4)
                                }
                            }

                            HStack(spacing: 8) {
                                HStack(spacing: 4) {
                                    Image(systemName: "arrow.down.circle.fill")
                                        .font(.caption2)
                                        .foregroundColor(.green)
                                    Text("\(model.pullsFormatted) pulls")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                if !model.labelsText.isEmpty {
                                    Text("•")
                                        .foregroundColor(.secondary)

                                    Text(model.labelsText)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            if let capability = model.capability {
                                Text(capability.capitalized)
                                    .font(.caption2)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color.purple.opacity(0.2))
                                    .foregroundColor(.purple)
                                    .cornerRadius(4)
                            }
                        }

                        Spacer()
                    }
                    .padding(24)
                    .background(Color.surfaceTertiary.opacity(0.3))

                    Divider()

                    // Model details and actions
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            // Download action
                            VStack(spacing: 12) {
                                if downloadingModel == model.modelIdentifier {
                                    // Downloading
                                    VStack(spacing: 8) {
                                        HStack(spacing: 8) {
                                            ProgressView()
                                                .scaleEffect(0.8)
                                            Text(downloadProgress ?? "Downloading...")
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }
                                        .padding(12)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color.surfaceSecondary.opacity(0.5))
                                        .cornerRadius(8)
                                    }
                                } else {
                                    // Download button
                                    Button(action: {
                                        Task {
                                            await downloadModel(model)
                                        }
                                    }) {
                                        Label("Download Model", systemImage: "arrow.down.circle")
                                            .frame(maxWidth: .infinity)
                                    }
                                    .buttonStyle(.borderedProminent)
                                }
                            }

                            // Description
                            if let description = model.description, !description.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Description")
                                        .font(.headline)

                                    Text(description)
                                        .font(.body)
                                        .foregroundColor(.secondary)
                                }
                            }

                            // Tags
                            if !model.tags.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Available Tags")
                                        .font(.headline)

                                    FlowLayout(spacing: 8) {
                                        ForEach(model.tags, id: \.self) { tag in
                                            Text(tag)
                                                .font(.caption)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 4)
                                                .background(Color.secondary.opacity(0.2))
                                                .foregroundColor(.secondary)
                                                .cornerRadius(4)
                                        }
                                    }
                                }
                            }

                            // Link to Ollama
                            if let url = URL(string: model.url) {
                                Button {
                                    NSWorkspace.shared.open(url)
                                } label: {
                                    Label("View on Ollama.com", systemImage: "arrow.up.right.square")
                                }
                                .buttonStyle(.link)
                            }
                        }
                        .padding()
                    }
                }
            } else {
                PaneEmptyState(
                    icon: "cube.box",
                    title: "Select a model",
                    subtitle: "Browse and download models from Ollama library"
                )
            }
        }
    }

    // MARK: - Data Loading

    private func loadModels(reset: Bool = false) async {
        if reset {
            currentPage = 0
        }

        await MainActor.run {
            isLoading = true
            error = nil
        }

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

            await MainActor.run {
                libraryModels = response.models
                totalCount = response.totalCount
                isLoading = false
            }
        } catch {
            await MainActor.run {
                self.error = error.localizedDescription
                isLoading = false
            }
        }
    }

    // MARK: - Download

    private func downloadModel(_ model: LibraryModel) async {
        await MainActor.run {
            downloadingModel = model.modelIdentifier
            downloadProgress = "Starting download..."
        }

        // Use the first tag as the model name to download
        let modelToDownload = model.tags.first ?? model.modelIdentifier

        ollamaService.pullModel(
            modelName: modelToDownload,
            onProgress: { progress in
                DispatchQueue.main.async {
                    self.downloadProgress = progress.message
                }
            },
            onComplete: { result in
                DispatchQueue.main.async {
                    self.downloadingModel = nil
                    self.downloadProgress = nil

                    switch result {
                    case .success:
                        // Could show success message
                        break
                    case .failure(let error):
                        self.error = error.localizedDescription
                    }
                }
            }
        )
    }
}

// MARK: - Supporting Views

struct LibraryModelRow: View {
    let model: LibraryModel
    let isSelected: Bool
    let isDownloading: Bool
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: model.isOfficial ? "checkmark.seal.fill" : "cube.box.fill")
                .font(.title3)
                .foregroundStyle(
                    model.isOfficial
                        ? LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
                        : LinearGradient.magnetarGradient
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(model.modelName)
                        .font(.headline)
                        .foregroundColor(.textPrimary)

                    if model.isOfficial {
                        Image(systemName: "checkmark.seal.fill")
                            .font(.caption)
                            .foregroundColor(.blue)
                    }
                }

                HStack(spacing: 6) {
                    Text("\(model.pullsFormatted) pulls")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if !model.labelsText.isEmpty {
                        Text("•")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Text(model.labelsText)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            if isDownloading {
                ProgressView()
                    .scaleEffect(0.7)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(backgroundColor)
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    private var backgroundColor: Color {
        if isSelected {
            return Color.magnetarPrimary.opacity(0.15)
        } else if isHovered {
            return Color.magnetarPrimary.opacity(0.06)
        } else {
            return Color.clear
        }
    }
}

// MARK: - Filter Enums

enum ModelTypeFilter: String, CaseIterable {
    case all = "all"
    case official = "official"
    case community = "community"

    var displayName: String {
        switch self {
        case .all: return "All"
        case .official: return "Official"
        case .community: return "Community"
        }
    }

    var apiValue: String? {
        self == .all ? nil : self.rawValue
    }
}

enum CapabilityFilter: String, CaseIterable {
    case all = "all"
    case code = "code"
    case chat = "chat"
    case vision = "vision"
    case embedding = "embedding"

    var displayName: String {
        switch self {
        case .all: return "All"
        case .code: return "Code"
        case .chat: return "Chat"
        case .vision: return "Vision"
        case .embedding: return "Embedding"
        }
    }

    var apiValue: String? {
        self == .all ? nil : self.rawValue
    }
}

enum SortOption: String, CaseIterable {
    case pulls = "pulls"
    case lastUpdated = "last_updated"

    var displayName: String {
        switch self {
        case .pulls: return "Most Popular"
        case .lastUpdated: return "Recently Updated"
        }
    }

    var apiValue: String {
        self.rawValue
    }
}

// MARK: - Preview

#Preview {
    ModelDiscoveryWorkspace()
        .frame(width: 1200, height: 800)
}
