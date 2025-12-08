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

    private var categoriesPane: some View {
        VStack(spacing: 0) {
            // Header with System Badge
            VStack(spacing: 8) {
                HStack {
                    Image(systemName: "cube.box.fill")
                        .font(.title2)
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    Text("MagnetarHub")
                        .font(.title3)
                        .fontWeight(.bold)

                    Spacer()
                }

                // System Info Badge
                HStack(spacing: 6) {
                    Image(systemName: "laptopcomputer")
                        .font(.caption)
                    Text(systemBadgeText)
                        .font(.caption)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(systemBadgeColor.opacity(0.2))
                .foregroundColor(systemBadgeColor)
                .cornerRadius(8)
            }
            .padding()

            Divider()

            // Categories
            List(HubCategory.allCases, selection: $selectedCategory) { category in
                CategoryRow(category: category)
                    .tag(category)
            }
            .listStyle(.sidebar)

            Divider()

            // Ollama Server Status
            VStack(spacing: 12) {
                HStack(spacing: 8) {
                    Circle()
                        .fill(ollamaServerRunning ? Color.green : Color.red)
                        .frame(width: 8, height: 8)

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Ollama Server")
                            .font(.caption)
                            .fontWeight(.medium)

                        Text(ollamaServerRunning ? "Running" : "Stopped")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    // Control buttons
                    HStack(spacing: 6) {
                        // Power button
                        Button {
                            Task {
                                await toggleOllama()
                            }
                        } label: {
                            Image(systemName: "power")
                                .font(.system(size: 11))
                                .foregroundColor(ollamaServerRunning ? .green : .red)
                        }
                        .buttonStyle(.plain)
                        .disabled(isOllamaActionInProgress)

                        // Restart button
                        Button {
                            Task {
                                await restartOllama()
                            }
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .font(.system(size: 11))
                                .foregroundColor(.magnetarPrimary)
                        }
                        .buttonStyle(.plain)
                        .disabled(isOllamaActionInProgress || !ollamaServerRunning)

                        if isOllamaActionInProgress {
                            ProgressView()
                                .scaleEffect(0.6)
                                .frame(width: 12, height: 12)
                        }
                    }
                }
                .padding(8)
                .background(Color.surfaceTertiary.opacity(0.3))
                .cornerRadius(6)

                // MagnetarCloud Status
                if isCloudAuthenticated {
                    // Signed In State
                    HStack(spacing: 8) {
                        Circle()
                            .fill(Color.green)
                            .frame(width: 8, height: 8)

                        VStack(alignment: .leading, spacing: 2) {
                            Text("MagnetarCloud")
                                .font(.caption)
                                .fontWeight(.medium)

                            Text("\(cloudUsername ?? "User") Connected")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }

                        Spacer()

                        // Control buttons
                        HStack(spacing: 6) {
                            // Disconnect button
                            Button {
                                Task {
                                    await disconnectCloud()
                                }
                            } label: {
                                Image(systemName: "power")
                                    .font(.system(size: 11))
                                    .foregroundColor(.green)
                            }
                            .buttonStyle(.plain)
                            .disabled(isCloudActionInProgress)

                            // Refresh button
                            Button {
                                Task {
                                    await reconnectCloud()
                                }
                            } label: {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 11))
                                    .foregroundColor(.magnetarPrimary)
                            }
                            .buttonStyle(.plain)
                            .disabled(isCloudActionInProgress)

                            if isCloudActionInProgress {
                                ProgressView()
                                    .scaleEffect(0.6)
                                    .frame(width: 12, height: 12)
                            }
                        }
                    }
                    .padding(8)
                    .background(Color.surfaceTertiary.opacity(0.3))
                    .cornerRadius(6)
                } else {
                    // Not Signed In State
                    HStack(spacing: 8) {
                        Circle()
                            .fill(Color.orange)
                            .frame(width: 8, height: 8)

                        VStack(alignment: .leading, spacing: 2) {
                            Text("MagnetarCloud")
                                .font(.caption)
                                .fontWeight(.medium)

                            Text("Not Connected")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }

                        Spacer()

                        Button {
                            Task {
                                await connectCloud()
                            }
                        } label: {
                            Text("Sign In")
                                .font(.caption2)
                                .fontWeight(.semibold)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.mini)
                        .disabled(isCloudActionInProgress)

                        if isCloudActionInProgress {
                            ProgressView()
                                .scaleEffect(0.6)
                                .frame(width: 12, height: 12)
                        }
                    }
                    .padding(8)
                    .background(Color.surfaceTertiary.opacity(0.3))
                    .cornerRadius(6)
                }
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
                discoverToolbar
                Divider()
            }

            // Cards grid
            ScrollView {
                if displayedModels.isEmpty {
                    emptyState
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

    private var discoverToolbar: some View {
        HStack(spacing: 12) {
            // Title
            Text("Recommended Models")
                .font(.headline)
                .foregroundColor(.primary)

            Spacer()

            // Network status indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(isNetworkConnected ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
                Text(isNetworkConnected ? "Online" : "Offline")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            // Browse Models button - Opens ollama.com
            Button {
                openOllamaWebsite()
            } label: {
                Label("Browse Models", systemImage: "safari")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            .disabled(!isNetworkConnected)
            .help(isNetworkConnected ? "Open Ollama library in browser" : "No internet connection")
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: selectedCategory.emptyIcon)
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text(selectedCategory.emptyTitle)
                .font(.title3)
                .fontWeight(.semibold)

            Text(selectedCategory.emptySubtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
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

// MARK: - Category Row

struct CategoryRow: View {
    let category: HubCategory

    var body: some View {
        Label {
            VStack(alignment: .leading, spacing: 2) {
                Text(category.displayName)
                    .font(.headline)
                Text(category.description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        } icon: {
            Image(systemName: category.icon)
                .foregroundStyle(LinearGradient.magnetarGradient)
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Model Card

struct ModelCard: View {
    let model: AnyModelItem
    let downloadProgress: DownloadProgress?
    let onDownload: () -> Void
    var enrichedMetadata: [String: EnrichedModelMetadata] = [:] // Add enriched metadata support
    @State private var isHovered: Bool = false
    private let capabilityService = SystemCapabilityService.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Icon + Badge + Compatibility
            HStack {
                Image(systemName: model.icon)
                    .font(.system(size: 32))
                    .foregroundStyle(model.iconGradient)

                Spacer()

                // Compatibility badge
                if let paramSize = model.parameterSize(enriched: enrichedMetadata) {
                    let compatibility = capabilityService.canRunModel(parameterSize: paramSize)
                    Image(systemName: compatibility.performance.icon)
                        .font(.caption2)
                        .foregroundColor(colorForPerformance(compatibility.performance))
                }

                // Multiple badges
                HStack(spacing: 4) {
                    ForEach(model.badges(enriched: enrichedMetadata), id: \.self) { badge in
                        Text(badge.uppercased())
                            .font(.caption2)
                            .fontWeight(.bold)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(model.badgeColor(for: badge).opacity(0.2))
                            .foregroundColor(model.badgeColor(for: badge))
                            .cornerRadius(4)
                    }
                }
            }

            // Title
            Text(model.displayName)
                .font(.headline)
                .lineLimit(1)

            // Description
            if let description = model.description(enriched: enrichedMetadata) {
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
                    .frame(height: 32, alignment: .top)
            }

            Spacer()

            // Download progress or stats
            if let progress = downloadProgress {
                VStack(spacing: 4) {
                    HStack {
                        Text(progress.status)
                            .font(.caption2)
                            .foregroundColor(progress.error != nil ? .red : .secondary)
                        Spacer()
                        if progress.error == nil {
                            Text("\(Int(progress.progress * 100))%")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                    ProgressView(value: progress.progress)
                        .tint(progress.error != nil ? .red : .magnetarPrimary)
                }
            } else if case .backendRecommended = model {
                Button {
                    onDownload()
                } label: {
                    Label("Download", systemImage: "arrow.down.circle")
                        .font(.caption)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            } else {
                // Info for local/cloud models - now shows as button hint
                VStack(spacing: 8) {
                    VStack(spacing: 6) {
                        if let stat1 = model.stat1 {
                            HStack(spacing: 6) {
                                Image(systemName: stat1.icon)
                                    .font(.caption2)
                                Text(stat1.text)
                                    .font(.caption2)
                                Spacer()
                            }
                            .foregroundColor(.secondary)
                        }

                        if let stat2 = model.stat2 {
                            HStack(spacing: 6) {
                                Image(systemName: stat2.icon)
                                    .font(.caption2)
                                Text(stat2.text)
                                    .font(.caption2)
                                Spacer()
                            }
                            .foregroundColor(.secondary)
                        }
                    }

                    // Visual hint that card is clickable
                    HStack {
                        Spacer()
                        Text("View Details")
                            .font(.caption2)
                            .foregroundColor(.magnetarPrimary.opacity(0.7))
                        Image(systemName: "chevron.right")
                            .font(.caption2)
                            .foregroundColor(.magnetarPrimary.opacity(0.7))
                    }
                }
            }
        }
        .padding(16)
        .frame(height: 200)
        .background(cardBackground)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .shadow(color: .black.opacity(isHovered ? 0.15 : 0.05), radius: isHovered ? 8 : 4, y: 2)
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isHovered)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    private var cardBackground: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(Color.surfaceSecondary.opacity(0.5))
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
            )
    }

    private func colorForPerformance(_ performance: ModelCompatibility.PerformanceLevel) -> Color {
        switch performance {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .insufficient: return .red
        case .unknown: return .secondary
        }
    }
}

// MARK: - Model Detail Modal

struct ModelDetailModal: View {
    let model: AnyModelItem
    let enrichedMetadata: [String: EnrichedModelMetadata]
    @Binding var activeDownloads: [String: DownloadProgress]
    let onDownload: (String) -> Void
    let onDelete: (String) -> Void
    let onUpdate: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    private let capabilityService = SystemCapabilityService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: model.icon)
                    .font(.system(size: 48))
                    .foregroundStyle(model.iconGradient)

                VStack(alignment: .leading, spacing: 4) {
                    Text(model.name)
                        .font(.title2)
                        .fontWeight(.bold)

                    // Multiple badges in detail modal
                    HStack(spacing: 6) {
                        ForEach(model.badges(enriched: enrichedMetadata), id: \.self) { badge in
                            Text(badge.uppercased())
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(model.badgeColor(for: badge).opacity(0.2))
                                .foregroundColor(model.badgeColor(for: badge))
                                .cornerRadius(6)
                        }
                    }
                }

                Spacer()

                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title2)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(24)

            Divider()

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // System Compatibility (for recommended models)
                    if case .backendRecommended(let backendModel) = model {
                        compatibilitySection(for: backendModel)
                    }

                    // Description
                    if let description = model.description(enriched: enrichedMetadata) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Description")
                                .font(.headline)
                            Text(description)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Actions
                    model.detailActions(
                        activeDownloads: $activeDownloads,
                        onDownload: onDownload,
                        onDelete: onDelete,
                        onUpdate: onUpdate
                    )

                    // Additional details
                    model.additionalDetails(enriched: enrichedMetadata)
                }
                .padding(24)
            }
        }
        .frame(width: 600, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    @ViewBuilder
    private func compatibilitySection(for backendModel: BackendRecommendedModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("System Compatibility")
                .font(.headline)

            // System info
            Text(capabilityService.getSystemSummary())
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.vertical, 4)

            // Use backend-provided compatibility info
            let performance = backendModel.compatibility.performance
            let icon = performanceIcon(for: performance)
            let color = colorForPerformanceString(performance)

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 12) {
                    Image(systemName: icon)
                        .foregroundColor(color)
                        .frame(width: 20)

                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) {
                            Text(friendlyModelSizeName(backendModel.parameterSize))
                                .font(.body)
                                .fontWeight(.medium)

                            Text("(\(backendModel.parameterSize))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        Text(backendModel.compatibility.reason)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    if let memUsage = backendModel.compatibility.estimatedMemoryUsage {
                        Text(String(format: "~%.1fGB", memUsage))
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding(10)
            .background(Color.surfaceTertiary.opacity(0.3))
            .cornerRadius(8)
        }
    }

    private func colorForPerformance(_ performance: ModelCompatibility.PerformanceLevel) -> Color {
        switch performance {
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .insufficient: return .red
        case .unknown: return .secondary
        }
    }

    private func colorForPerformanceString(_ performance: String) -> Color {
        switch performance.lowercased() {
        case "excellent": return .green
        case "good": return .blue
        case "fair": return .orange
        case "insufficient": return .red
        default: return .secondary
        }
    }

    private func performanceIcon(for performance: String) -> String {
        switch performance.lowercased() {
        case "excellent": return "checkmark.circle.fill"
        case "good": return "checkmark.circle"
        case "fair": return "exclamationmark.triangle"
        case "insufficient": return "xmark.circle"
        default: return "questionmark.circle"
        }
    }

    private func friendlyModelSizeName(_ size: String) -> String {
        switch size {
        case "1.5B": return "Tiny"
        case "3B": return "Small"
        case "7B": return "Medium"
        case "13B": return "Large"
        case "34B": return "Very Large"
        case "70B": return "Massive"
        default: return size
        }
    }
}

// MARK: - Hub Category

enum HubCategory: String, CaseIterable, Identifiable {
    case myModels = "my_models"
    case discover = "discover"
    case cloud = "cloud"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .myModels: return "My Models"
        case .discover: return "Discover"
        case .cloud: return "Cloud Models"
        }
    }

    var description: String {
        switch self {
        case .myModels: return "Installed local models"
        case .discover: return "Browse Ollama library"
        case .cloud: return "MagnetarCloud models"
        }
    }

    var icon: String {
        switch self {
        case .myModels: return "cube.box"
        case .discover: return "magnifyingglass"
        case .cloud: return "cloud"
        }
    }

    var emptyIcon: String {
        switch self {
        case .myModels: return "cube.box"
        case .discover: return "magnifyingglass.circle"
        case .cloud: return "cloud"
        }
    }

    var emptyTitle: String {
        switch self {
        case .myModels: return "No Models Installed"
        case .discover: return "No Models Found"
        case .cloud: return "Not Connected"
        }
    }

    var emptySubtitle: String {
        switch self {
        case .myModels: return "Download models from Discover tab"
        case .discover: return "Try a different search"
        case .cloud: return "Sign in to MagnetarCloud"
        }
    }
}

// MARK: - AnyModelItem (Type-erased model)

enum AnyModelItem: Identifiable {
    case local(OllamaModel)
    case backendRecommended(BackendRecommendedModel)
    case cloud(OllamaModel)

    var id: String {
        switch self {
        case .local(let model): return "local-\(model.id)"
        case .backendRecommended(let model): return "recommended-\(model.id)"
        case .cloud(let model): return "cloud-\(model.id)"
        }
    }

    var name: String {
        switch self {
        case .local(let model): return model.name
        case .backendRecommended(let model): return model.modelName
        case .cloud(let model): return model.name
        }
    }

    var displayName: String {
        switch self {
        case .local(let model): return model.name
        case .backendRecommended(let model): return model.displayName
        case .cloud(let model): return model.name
        }
    }

    func description(enriched: [String: EnrichedModelMetadata]) -> String? {
        switch self {
        case .local(let model):
            // Use enriched metadata if available
            if let metadata = enriched[model.name] {
                return metadata.description
            }
            // Fallback to basic description
            let name = model.name.lowercased()
            if name.contains("llama") {
                return "Meta's powerful open-source language model"
            } else if name.contains("mistral") {
                return "High-performance model with excellent reasoning"
            } else if name.contains("phi") {
                return "Microsoft's efficient small language model"
            } else if name.contains("qwen") {
                return "Multilingual model with strong capabilities"
            } else if name.contains("gemma") {
                return "Google's lightweight open model"
            } else if name.contains("deepseek") {
                return "Advanced reasoning and coding model"
            } else if name.contains("command") {
                return "Cohere's enterprise-grade language model"
            } else if name.contains("mixtral") {
                return "Mixture-of-experts model with superior performance"
            } else {
                return "Locally installed language model"
            }
        case .backendRecommended(let model): return model.description
        case .cloud: return nil
        }
    }

    var icon: String {
        switch self {
        case .local: return "cube.box.fill"
        case .backendRecommended: return "star.circle.fill"
        case .cloud: return "cloud.fill"
        }
    }

    var iconGradient: LinearGradient {
        switch self {
        case .local: return LinearGradient.magnetarGradient
        case .backendRecommended:
            return LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .cloud: return LinearGradient(colors: [.purple, .pink], startPoint: .topLeading, endPoint: .bottomTrailing)
        }
    }

    func badges(enriched: [String: EnrichedModelMetadata]) -> [String] {
        switch self {
        case .local(let model):
            if let metadata = enriched[model.name] {
                return metadata.badges
            }
            return ["installed"]
        case .backendRecommended(let model):
            var result = model.badges
            if model.isInstalled && !result.contains("installed") {
                result.insert("installed", at: 0)
            }
            return result
        case .cloud: return ["cloud"]
        }
    }

    func badgeColor(for badge: String) -> Color {
        switch badge.lowercased() {
        case "installed": return .green
        case "recommended": return .blue
        case "experimental": return .orange
        case "local": return .green
        case "cloud": return .purple
        default: return .gray
        }
    }

    func parameterSize(enriched: [String: EnrichedModelMetadata]) -> String? {
        switch self {
        case .local(let model):
            if let metadata = enriched[model.name] {
                return metadata.parameterSize
            }
            return model.details?.parameterSize
        case .backendRecommended(let model): return model.parameterSize
        case .cloud: return nil
        }
    }

    func isMultiPurpose(enriched: [String: EnrichedModelMetadata]) -> Bool {
        switch self {
        case .local(let model):
            if let metadata = enriched[model.name] {
                return metadata.isMultiPurpose
            }
            return false
        case .backendRecommended(let model): return model.isMultiPurpose
        case .cloud: return false
        }
    }

    func primaryUseCases(enriched: [String: EnrichedModelMetadata]) -> [String] {
        switch self {
        case .local(let model):
            if let metadata = enriched[model.name] {
                return metadata.primaryUseCases
            }
            return []
        case .backendRecommended(let model): return model.primaryUseCases
        case .cloud: return []
        }
    }

    var stat1: (icon: String, text: String)? {
        switch self {
        case .local(let model):
            return ("internaldrive", model.sizeFormatted)
        case .backendRecommended(let model):
            return ("tag", model.parameterSize)
        case .cloud(let model):
            return ("internaldrive", model.sizeFormatted)
        }
    }

    var stat2: (icon: String, text: String)? {
        switch self {
        case .local(let model):
            // Show model family/type
            let name = model.name.lowercased()
            if name.contains("instruct") || name.contains("chat") {
                return ("message.fill", "Chat")
            } else if name.contains("code") {
                return ("chevron.left.forwardslash.chevron.right", "Code")
            } else if name.contains("vision") || name.contains("llava") {
                return ("eye.fill", "Vision")
            } else {
                return ("sparkles", "General")
            }
        case .backendRecommended(let model):
            if model.isMultiPurpose {
                return ("star.circle", "Multi-purpose")
            } else {
                return ("sparkles", model.capability.capitalized)
            }
        case .cloud: return nil
        }
    }

    func detailActions(
        activeDownloads: Binding<[String: DownloadProgress]>,
        onDownload: @escaping (String) -> Void,
        onDelete: @escaping (String) -> Void,
        onUpdate: @escaping (String) -> Void
    ) -> some View {
        Group {
            switch self {
            case .local(let model):
                VStack(alignment: .leading, spacing: 12) {
                    Text("Actions")
                        .font(.headline)

                    HStack(spacing: 12) {
                        Button {
                            onDelete(model.name)
                        } label: {
                            Label("Delete", systemImage: "trash")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .tint(.red)

                        Button {
                            onUpdate(model.name)
                        } label: {
                            Label("Update", systemImage: "arrow.clockwise")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                    }

                    if !model.sizeFormatted.isEmpty {
                        HStack {
                            Image(systemName: "internaldrive")
                                .foregroundColor(.secondary)
                            Text("Size: \(model.sizeFormatted)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }

            case .backendRecommended(let model):
                VStack(alignment: .leading, spacing: 12) {
                    Text("Download")
                        .font(.headline)

                    if let progress = activeDownloads.wrappedValue[model.modelName] {
                        // Show progress
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(progress.status)
                                    .font(.caption)
                                    .foregroundColor(progress.error != nil ? .red : .secondary)
                                Spacer()
                                if progress.error == nil {
                                    Text("\(Int(progress.progress * 100))%")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                            ProgressView(value: progress.progress)
                                .tint(progress.error != nil ? .red : .magnetarPrimary)
                        }
                        .padding()
                        .background(Color.surfaceTertiary.opacity(0.3))
                        .cornerRadius(8)
                    } else {
                        Button {
                            onDownload(model.modelName)
                        } label: {
                            Label("Download \(model.displayName)", systemImage: "arrow.down.circle")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }

            case .cloud:
                VStack(alignment: .leading, spacing: 12) {
                    Text("Cloud Actions")
                        .font(.headline)

                    Button {
                        // TODO: Sync from cloud
                    } label: {
                        Label("Sync to Local", systemImage: "arrow.down.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
        }
    }

    @ViewBuilder
    func additionalDetails(enriched: [String: EnrichedModelMetadata]) -> some View {
        switch self {
        case .local(let model):
            VStack(alignment: .leading, spacing: 8) {
                Text("About")
                    .font(.headline)

                // Use enriched metadata if available
                if let metadata = enriched[model.name] {
                    // Multi-purpose or capability
                    if metadata.isMultiPurpose {
                        HStack(spacing: 6) {
                            Image(systemName: "star.circle")
                                .font(.caption)
                                .foregroundColor(.magnetarPrimary)
                            Text("Multi-Purpose: \(metadata.primaryUseCases.joined(separator: ", "))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    } else {
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                                .font(.caption)
                                .foregroundColor(.magnetarPrimary)
                            Text("Capability: \(metadata.capability.capitalized)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Parameter size
                    if let paramSize = metadata.parameterSize {
                        HStack(spacing: 6) {
                            Image(systemName: "tag")
                                .font(.caption)
                                .foregroundColor(.magnetarPrimary)
                            Text("Size: \(paramSize)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Strengths
                    if !metadata.strengths.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Strengths:")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(.secondary)
                            ForEach(metadata.strengths, id: \.self) { strength in
                                HStack(spacing: 4) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.caption2)
                                        .foregroundColor(.green)
                                    Text(strength)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .padding(.top, 4)
                    }

                    // Ideal for
                    if !metadata.idealFor.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Ideal For:")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundColor(.secondary)
                            Text(metadata.idealFor)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 4)
                    }
                } else {
                    // Fallback: basic model info
                    if let family = model.details?.family {
                        HStack {
                            Text("Family:")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text(family)
                                .font(.caption)
                        }
                    }

                    if let digest = model.digest {
                        HStack {
                            Text("Digest:")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text(digest.prefix(12))
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                }
            }

        case .backendRecommended(let model):
            VStack(alignment: .leading, spacing: 8) {
                Text("About")
                    .font(.headline)

                if model.isMultiPurpose {
                    HStack(spacing: 6) {
                        Image(systemName: "star.circle")
                            .font(.caption)
                            .foregroundColor(.magnetarPrimary)
                        Text("Multi-Purpose: \(model.primaryUseCases.joined(separator: ", "))")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                } else {
                    HStack(spacing: 6) {
                        Image(systemName: "sparkles")
                            .font(.caption)
                            .foregroundColor(.magnetarPrimary)
                        Text("Capability: \(model.capability.capitalized)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                HStack(spacing: 6) {
                    Image(systemName: "tag")
                        .font(.caption)
                        .foregroundColor(.magnetarPrimary)
                    Text("Size: \(model.parameterSize)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

        case .cloud:
            EmptyView()
        }
    }
}

// MARK: - Recommended Model

struct RecommendedModel: Identifiable {
    let modelName: String
    let displayName: String
    let description: String
    let capability: String
    let parameterSize: String
    let isOfficial: Bool

    var id: String { modelName }
}

// MARK: - Download Progress

struct DownloadProgress {
    let modelName: String
    let status: String
    let progress: Double
    var error: String? = nil
}

// MARK: - Preview

#Preview {
    MagnetarHubWorkspace()
        .frame(width: 1200, height: 800)
}
