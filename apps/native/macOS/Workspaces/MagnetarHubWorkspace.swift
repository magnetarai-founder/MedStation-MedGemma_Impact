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

    // Discovery - Now using hardcoded recommendations
    @State private var showDownloadModelModal: Bool = false
    @State private var isNetworkConnected: Bool = false

    // Cloud models
    @State private var cloudModels: [OllamaModel] = []
    @State private var isCloudAuthenticated: Bool = false
    @State private var isLoadingCloud: Bool = false
    @State private var isCloudActionInProgress: Bool = false
    @State private var cloudUsername: String? = nil

    // Download tracking
    @State private var activeDownloads: [String: DownloadProgress] = [:]

    private let ollamaService = OllamaService.shared
    private let capabilityService = SystemCapabilityService.shared
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
                ModelDetailModal(model: model, activeDownloads: $activeDownloads, onDownload: downloadModel)
            }
        }
        .sheet(isPresented: $showDownloadModelModal) {
            DownloadModelModal(
                isPresented: $showDownloadModelModal,
                onDownload: downloadModel,
                isNetworkConnected: isNetworkConnected,
                ollamaServerRunning: ollamaServerRunning
            )
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
                                }
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                selectedModel = model
                                showModelDetail = true
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

            // Download Model button - Opens modal
            Button {
                showDownloadModelModal = true
            } label: {
                Label("Download Model", systemImage: "arrow.down.circle")
                    .font(.caption)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!isNetworkConnected || !ollamaServerRunning)
            .help(downloadButtonTooltip)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }

    private var downloadButtonTooltip: String {
        if !isNetworkConnected {
            return "No internet connection"
        } else if !ollamaServerRunning {
            return "Ollama server is not running"
        } else {
            return "Download a specific model by name"
        }
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

        // Load cloud auth status
        // TODO: Add cloud auth check
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
            return recommendedModels.map { AnyModelItem.recommended($0) }
        case .cloud:
            return cloudModels.map { AnyModelItem.cloud($0) }
        }
    }

    // Hardcoded recommended models
    private var recommendedModels: [RecommendedModel] {
        let allModels: [RecommendedModel] = [
            RecommendedModel(
                modelName: "phi4:14b",
                displayName: "Phi-4 (14B)",
                description: "Microsoft's powerful small model - excellent reasoning and coding abilities in a compact size",
                capability: "code",
                parameterSize: "14B",
                isOfficial: true
            ),
            RecommendedModel(
                modelName: "llama3.3:70b",
                displayName: "Llama 3.3 (70B)",
                description: "Meta's flagship model - top-tier performance for complex tasks and reasoning",
                capability: "chat",
                parameterSize: "70B",
                isOfficial: true
            ),
            RecommendedModel(
                modelName: "qwen2.5-coder:14b",
                displayName: "Qwen2.5 Coder (14B)",
                description: "Specialized coding model - great for code generation and debugging",
                capability: "code",
                parameterSize: "14B",
                isOfficial: true
            ),
            RecommendedModel(
                modelName: "mistral:7b",
                displayName: "Mistral (7B)",
                description: "Fast and efficient - perfect balance of performance and speed",
                capability: "chat",
                parameterSize: "7B",
                isOfficial: true
            ),
            RecommendedModel(
                modelName: "llama3.2:3b",
                displayName: "Llama 3.2 (3B)",
                description: "Lightweight and fast - ideal for quick tasks and low-resource devices",
                capability: "chat",
                parameterSize: "3B",
                isOfficial: true
            ),
            RecommendedModel(
                modelName: "deepseek-r1:14b",
                displayName: "DeepSeek R1 (14B)",
                description: "Advanced reasoning model - excels at complex problem-solving and analysis",
                capability: "chat",
                parameterSize: "14B",
                isOfficial: true
            ),
        ]

        // Filter by system capability
        return allModels.filter { model in
            let compatibility = capabilityService.canRunModel(parameterSize: model.parameterSize)
            return compatibility.performance != .insufficient
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
                if let paramSize = model.parameterSize {
                    let compatibility = capabilityService.canRunModel(parameterSize: paramSize)
                    Image(systemName: compatibility.performance.icon)
                        .font(.caption2)
                        .foregroundColor(colorForPerformance(compatibility.performance))
                }

                if let badge = model.badge {
                    Text(badge)
                        .font(.caption2)
                        .fontWeight(.bold)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(model.badgeColor.opacity(0.2))
                        .foregroundColor(model.badgeColor)
                        .cornerRadius(6)
                }
            }

            // Title
            Text(model.displayName)
                .font(.headline)
                .lineLimit(1)

            // Description
            if let description = model.description {
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
            } else if case .recommended = model {
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
                // Stats for local/cloud models
                HStack(spacing: 12) {
                    if let stat1 = model.stat1 {
                        HStack(spacing: 4) {
                            Image(systemName: stat1.icon)
                                .font(.caption2)
                            Text(stat1.text)
                                .font(.caption2)
                        }
                        .foregroundColor(.secondary)
                    }

                    if let stat2 = model.stat2 {
                        HStack(spacing: 4) {
                            Image(systemName: stat2.icon)
                                .font(.caption2)
                            Text(stat2.text)
                                .font(.caption2)
                        }
                        .foregroundColor(.secondary)
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

// MARK: - Download Model Modal

struct DownloadModelModal: View {
    @Binding var isPresented: Bool
    let onDownload: (String) -> Void
    let isNetworkConnected: Bool
    let ollamaServerRunning: Bool

    @State private var modelName: String = ""
    @FocusState private var isTextFieldFocused: Bool

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Image(systemName: "arrow.down.circle.fill")
                    .font(.title2)
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("Download Model")
                    .font(.title3)
                    .fontWeight(.bold)

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Instructions
            VStack(alignment: .leading, spacing: 8) {
                Text("Enter the exact model name from the Ollama library")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Text("Example: phi4:14b, llama3.3:70b, mistral:7b")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .italic()
            }

            // Text field
            TextField("Type/Paste model in exact format from ollama library (ex. phi4:14b)", text: $modelName)
                .textFieldStyle(.roundedBorder)
                .focused($isTextFieldFocused)
                .onSubmit {
                    downloadModel()
                }

            // Status indicators
            HStack(spacing: 16) {
                HStack(spacing: 6) {
                    Image(systemName: isNetworkConnected ? "wifi" : "wifi.slash")
                        .foregroundColor(isNetworkConnected ? .green : .red)
                    Text(isNetworkConnected ? "Connected" : "No internet")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                HStack(spacing: 6) {
                    Image(systemName: ollamaServerRunning ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundColor(ollamaServerRunning ? .green : .red)
                    Text(ollamaServerRunning ? "Ollama running" : "Ollama stopped")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            // Buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .keyboardShortcut(.cancelAction)

                Button("Download") {
                    downloadModel()
                }
                .keyboardShortcut(.defaultAction)
                .disabled(!canDownload)
            }
        }
        .padding(24)
        .frame(width: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .onAppear {
            isTextFieldFocused = true
        }
    }

    private var canDownload: Bool {
        !modelName.isEmpty && isNetworkConnected && ollamaServerRunning
    }

    private func downloadModel() {
        guard canDownload else { return }
        onDownload(modelName.trimmingCharacters(in: .whitespaces))
        isPresented = false
    }
}

// MARK: - Model Detail Modal

struct ModelDetailModal: View {
    let model: AnyModelItem
    @Binding var activeDownloads: [String: DownloadProgress]
    let onDownload: (String) -> Void
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

                    if let badge = model.badge {
                        Text(badge)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(model.badgeColor.opacity(0.2))
                            .foregroundColor(model.badgeColor)
                            .cornerRadius(6)
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
                    if case .recommended(let recommendedModel) = model {
                        compatibilitySection(for: recommendedModel)
                    }

                    // Description
                    if let description = model.description {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Description")
                                .font(.headline)
                            Text(description)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Actions
                    model.detailActions(activeDownloads: $activeDownloads, onDownload: onDownload)

                    // Additional details
                    model.additionalDetails
                }
                .padding(24)
            }
        }
        .frame(width: 600, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    @ViewBuilder
    private func compatibilitySection(for recommendedModel: RecommendedModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("System Compatibility")
                .font(.headline)

            // System info
            Text(capabilityService.getSystemSummary())
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.vertical, 4)

            // Check compatibility for this model size
            let compatibility = capabilityService.canRunModel(parameterSize: recommendedModel.parameterSize)

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 12) {
                    Image(systemName: compatibility.performance.icon)
                        .foregroundColor(colorForPerformance(compatibility.performance))
                        .frame(width: 20)

                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) {
                            Text(friendlyModelSizeName(recommendedModel.parameterSize))
                                .font(.body)
                                .fontWeight(.medium)

                            Text("(\(recommendedModel.parameterSize))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        Text(compatibility.reason)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    if let memUsage = compatibility.estimatedMemoryUsage {
                        Text(String(format: "~%.1fGB", memUsage))
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }

                if let explanation = compatibility.friendlyExplanation {
                    Text(explanation)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .padding(.leading, 32)
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
    case recommended(RecommendedModel)
    case cloud(OllamaModel)

    var id: String {
        switch self {
        case .local(let model): return "local-\(model.id)"
        case .recommended(let model): return "recommended-\(model.id)"
        case .cloud(let model): return "cloud-\(model.id)"
        }
    }

    var name: String {
        switch self {
        case .local(let model): return model.name
        case .recommended(let model): return model.modelName
        case .cloud(let model): return model.name
        }
    }

    var displayName: String {
        switch self {
        case .local(let model): return model.name
        case .recommended(let model): return model.displayName
        case .cloud(let model): return model.name
        }
    }

    var description: String? {
        switch self {
        case .local: return nil
        case .recommended(let model): return model.description
        case .cloud: return nil
        }
    }

    var icon: String {
        switch self {
        case .local: return "cube.box.fill"
        case .recommended: return "star.circle.fill"
        case .cloud: return "cloud.fill"
        }
    }

    var iconGradient: LinearGradient {
        switch self {
        case .local: return LinearGradient.magnetarGradient
        case .recommended:
            return LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .cloud: return LinearGradient(colors: [.purple, .pink], startPoint: .topLeading, endPoint: .bottomTrailing)
        }
    }

    var badge: String? {
        switch self {
        case .local: return "LOCAL"
        case .recommended(let model): return model.isOfficial ? "RECOMMENDED" : nil
        case .cloud: return "CLOUD"
        }
    }

    var badgeColor: Color {
        switch self {
        case .local: return .green
        case .recommended: return .blue
        case .cloud: return .purple
        }
    }

    var parameterSize: String? {
        switch self {
        case .local: return nil
        case .recommended(let model): return model.parameterSize
        case .cloud: return nil
        }
    }

    var stat1: (icon: String, text: String)? {
        switch self {
        case .local(let model):
            return ("internaldrive", model.sizeFormatted)
        case .recommended(let model):
            return ("tag", model.parameterSize)
        case .cloud(let model):
            return ("internaldrive", model.sizeFormatted)
        }
    }

    var stat2: (icon: String, text: String)? {
        switch self {
        case .local: return nil
        case .recommended(let model):
            return ("sparkles", model.capability.capitalized)
        case .cloud: return nil
        }
    }

    func detailActions(activeDownloads: Binding<[String: DownloadProgress]>, onDownload: @escaping (String) -> Void) -> some View {
        Group {
            switch self {
            case .local(let model):
                VStack(alignment: .leading, spacing: 12) {
                    Text("Actions")
                        .font(.headline)

                    HStack(spacing: 12) {
                        Button {
                            // TODO: Delete model
                        } label: {
                            Label("Delete", systemImage: "trash")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .tint(.red)

                        Button {
                            // TODO: Update model
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

            case .recommended(let model):
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
    var additionalDetails: some View {
        switch self {
        case .local(let model):
            VStack(alignment: .leading, spacing: 8) {
                Text("Model Info")
                    .font(.headline)

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

        case .recommended(let model):
            VStack(alignment: .leading, spacing: 8) {
                Text("About")
                    .font(.headline)

                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.caption)
                        .foregroundColor(.magnetarPrimary)
                    Text("Capability: \(model.capability.capitalized)")
                        .font(.caption)
                        .foregroundColor(.secondary)
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
