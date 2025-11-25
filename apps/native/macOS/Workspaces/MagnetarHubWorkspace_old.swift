//
//  MagnetarHubWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Model management and dev portal.
//

import SwiftUI

struct MagnetarHubWorkspace: View {
    @Environment(UserStore.self) private var userStore

    @State private var modelsStore = ModelsStore()
    @State private var selectedTab: HubTab = .localModels
    @State private var isCloudAuthenticated: Bool = false
    @State private var editingModel: OllamaModel?
    @State private var showTagEditor: Bool = false
    @State private var ollamaServerRunning: Bool = false
    @State private var isCheckingOllama: Bool = false
    @State private var showSidebar: Bool = true

    var body: some View {
        // Just show the main content - nav rail and sidebar are handled by MainAppView
        hubContent
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        .sheet(isPresented: $showTagEditor) {
            if let model = editingModel {
                TagEditorSheet(model: model, onSave: { updatedModel in
                    // TODO: Save updated tags to backend
                    showTagEditor = false
                })
            }
        }
    }

    // MARK: - Navigation Rail

    private var navigationRail: some View {
        VStack(spacing: 0) {
            // MagnetarHub icon at top
            VStack(spacing: 4) {
                Image(systemName: "cube.box.fill")
                    .font(.title2)
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("Hub")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            .frame(height: 60)
            .frame(maxWidth: .infinity)

            Divider()

            // Tab buttons
            VStack(spacing: 4) {
                ForEach(HubTab.allCases) { tab in
                    Button {
                        selectedTab = tab
                    } label: {
                        VStack(spacing: 4) {
                            Image(systemName: tab.icon)
                                .font(.title3)

                            Text(tab.shortName)
                                .font(.caption2)
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 64)
                        .background(selectedTab == tab ? Color.magnetarPrimary.opacity(0.2) : Color.clear)
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(selectedTab == tab ? .magnetarPrimary : .secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 4)

            Spacer()

            // Sidebar toggle at bottom
            Button {
                withAnimation {
                    showSidebar.toggle()
                }
            } label: {
                VStack(spacing: 4) {
                    Image(systemName: showSidebar ? "sidebar.left" : "sidebar.right")
                        .font(.title3)

                    Text("Info")
                        .font(.caption2)
                }
                .frame(maxWidth: .infinity)
                .frame(height: 60)
            }
            .buttonStyle(.plain)
            .foregroundColor(.magnetarPrimary)
            .help(showSidebar ? "Hide System Status" : "Show System Status")
        }
        .task {
            await checkOllamaStatus()
        }
    }

    // MARK: - Hub Content

    @ViewBuilder
    private var hubContent: some View {
        switch selectedTab {
        case .localModels:
            localModelsView
        case .cloudModels:
            cloudModelsView
        case .performance:
            performanceView
        case .settings:
            modelSettingsView
        }
    }

    // MARK: - Local Models View

    private var localModelsView: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Local Models")
                        .font(.title2)
                        .fontWeight(.semibold)

                    if !modelsStore.models.isEmpty {
                        Text("\(modelsStore.models.count) models installed")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                if modelsStore.isLoading {
                    ProgressView()
                        .scaleEffect(0.8)
                } else {
                    Button {
                        Task {
                            await modelsStore.fetchModels()
                        }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.bordered)

                    Button {
                        // TODO: Auto-detect tags for all models
                        // This will reset all models to their auto-detected tags
                    } label: {
                        Label("Auto-detect All Tags", systemImage: "sparkles")
                    }
                    .buttonStyle(.bordered)

                    Button {
                        // TODO: Pull new model
                    } label: {
                        Label("Pull Model", systemImage: "arrow.down.circle")
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding()

            Divider()

            // Models grid
            if modelsStore.models.isEmpty && !modelsStore.isLoading {
                emptyModelsView
            } else {
                ScrollView {
                    LazyVGrid(columns: [
                        GridItem(.adaptive(minimum: 280, maximum: 320), spacing: 16)
                    ], spacing: 16) {
                        ForEach(modelsStore.models) { model in
                            modelCard(model: model)
                        }
                    }
                    .padding()
                }
            }
        }
        .task {
            // Fetch models when view appears
            if modelsStore.models.isEmpty {
                await modelsStore.fetchModels()
            }
        }
    }

    private var emptyModelsView: some View {
        VStack(spacing: 16) {
            Image(systemName: "cube.box")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("No Models Installed")
                .font(.headline)

            Text("Pull a model from Ollama to get started")
                .font(.caption)
                .foregroundColor(.secondary)

            Button {
                // TODO: Show model browser
            } label: {
                Label("Browse Models", systemImage: "magnifyingglass")
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Cloud Models View

    private var cloudModelsView: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Cloud Models")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()
            }
            .padding()

            Divider()

            VStack(spacing: 24) {
                if !isCloudAuthenticated {
                // Not authenticated
                VStack(spacing: 16) {
                    Image(systemName: "cloud.slash")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)

                    Text("Connect to MagnetarCloud")
                        .font(.title2)
                        .fontWeight(.semibold)

                    Text("Sign in to access your fine-tuned models and sync across devices")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 400)

                    Button {
                        // TODO: Open Settings > MagnetarCloud
                    } label: {
                        Label("Login to MagnetarCloud Account", systemImage: "person.circle")
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                // Authenticated - show cloud models
                VStack(spacing: 0) {
                    Text("Your Fine-Tuned Models")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()

                    Divider()

                    // Cloud models grid (placeholder)
                    ScrollView {
                        LazyVGrid(columns: [
                            GridItem(.adaptive(minimum: 280, maximum: 320), spacing: 16)
                        ], spacing: 16) {
                            ForEach(0..<3) { index in
                                cloudModelCard(name: "your-model-v1", size: "7B", lastUpdated: "2 days ago")
                            }
                        }
                        .padding()
                    }
                }
            }
        }
    }
    }

    // MARK: - Performance View

    private var performanceView: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Performance")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()
            }
            .padding()

            Divider()

            VStack(spacing: 24) {
            Image(systemName: "chart.xyaxis.line")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("Performance Metrics")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Model performance tracking coming soon")
                .font(.body)
                .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Model Settings View

    private var modelSettingsView: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Settings")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()
            }
            .padding()

            Divider()

            VStack(spacing: 24) {
                Image(systemName: "gearshape.2")
                    .font(.system(size: 48))
                    .foregroundColor(.secondary)

                Text("Model Settings")
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("Configure model parameters and defaults")
                    .font(.body)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Model Card Components

    @ViewBuilder
    private func modelCard(model: OllamaModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Model icon and name
            HStack(spacing: 12) {
                Image(systemName: "cube.fill")
                    .font(.title)
                    .foregroundStyle(LinearGradient.magnetarGradient)

                VStack(alignment: .leading, spacing: 2) {
                    Text(model.name)
                        .font(.headline)
                        .lineLimit(1)

                    Text(model.size)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }

            // Status
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.caption)

                Text("Installed")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            if let modifiedAt = model.modifiedAt {
                HStack {
                    Image(systemName: "clock")
                        .foregroundColor(.secondary)
                        .font(.caption)

                    Text("Modified: \(formatDate(modifiedAt))")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            // Tags
            if let tagDetails = model.tagDetails, !tagDetails.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 4) {
                        Text("Capabilities:")
                            .font(.caption2)
                            .foregroundColor(.secondary)

                        Spacer()

                        Button {
                            editingModel = model
                            showTagEditor = true
                        } label: {
                            HStack(spacing: 2) {
                                Image(systemName: "pencil")
                                    .font(.caption2)
                                Text("Edit")
                                    .font(.caption2)
                            }
                        }
                        .buttonStyle(.plain)
                        .foregroundColor(.magnetarPrimary)
                    }

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach(tagDetails) { tag in
                                HStack(spacing: 4) {
                                    Text(tag.icon)
                                        .font(.caption2)
                                    Text(tag.name)
                                        .font(.caption2)
                                        .fontWeight(.medium)
                                }
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.magnetarPrimary.opacity(0.15))
                                .cornerRadius(6)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 6)
                                        .stroke(Color.magnetarPrimary.opacity(0.3), lineWidth: 0.5)
                                )
                            }
                        }
                    }
                    .frame(height: 24)
                }
            }

            Divider()

            // Actions
            HStack(spacing: 8) {
                Button {
                    // TODO: Use model in chat
                } label: {
                    Text("Use")
                        .font(.caption)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Button {
                    // TODO: Update model
                } label: {
                    Text("Update")
                        .font(.caption)
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Spacer()

                Button {
                    Task {
                        try? await modelsStore.deleteModel(name: model.name)
                    }
                } label: {
                    Image(systemName: "trash")
                        .font(.caption)
                }
                .buttonStyle(.borderless)
                .controlSize(.small)
                .foregroundColor(.red)
            }
        }
        .padding()
        .background(Color.surfaceSecondary.opacity(0.5))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.surfaceTertiary.opacity(0.3), lineWidth: 1)
        )
    }

    private func formatDate(_ dateString: String) -> String {
        // Simple date formatting - could be improved
        if let index = dateString.firstIndex(of: "T") {
            return String(dateString[..<index])
        }
        return dateString
    }

    @ViewBuilder
    private func cloudModelCard(name: String, size: String, lastUpdated: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Model icon and name
            HStack(spacing: 12) {
                Image(systemName: "cloud.fill")
                    .font(.title)
                    .foregroundStyle(LinearGradient.magnetarGradient)

                VStack(alignment: .leading, spacing: 2) {
                    Text(name)
                        .font(.headline)
                        .lineLimit(1)

                    Text(size)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }

            // Last updated
            HStack {
                Image(systemName: "clock")
                    .foregroundColor(.secondary)
                    .font(.caption)

                Text("Updated \(lastUpdated)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Divider()

            // Actions
            HStack(spacing: 8) {
                Button {
                    // TODO: Download model
                } label: {
                    Label("Download", systemImage: "arrow.down.circle")
                        .font(.caption)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)

                Spacer()
            }
        }
        .padding()
        .background(Color.surfaceSecondary.opacity(0.5))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.magnetarPrimary.opacity(0.3), lineWidth: 1)
        )
    }

    // MARK: - System Status Panel

    private var systemStatusPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("System Status")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            // Ollama Server Status
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

                if isCheckingOllama {
                    ProgressView()
                        .scaleEffect(0.6)
                } else {
                    Button {
                        Task {
                            if ollamaServerRunning {
                                // TODO: Stop Ollama
                            } else {
                                await startOllama()
                            }
                        }
                    } label: {
                        Image(systemName: ollamaServerRunning ? "stop.circle" : "play.circle")
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.magnetarPrimary)
                }
            }
            .padding(8)
            .background(Color.surfaceTertiary.opacity(0.3))
            .cornerRadius(6)

            // MagnetarCloud Status
            HStack(spacing: 8) {
                Circle()
                    .fill(isCloudAuthenticated ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)

                VStack(alignment: .leading, spacing: 2) {
                    Text("MagnetarCloud")
                        .font(.caption)
                        .fontWeight(.medium)

                    Text(isCloudAuthenticated ? "Connected" : "Not connected")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button {
                    // TODO: Open MagnetarCloud settings
                } label: {
                    Image(systemName: isCloudAuthenticated ? "link.circle" : "link.circle.fill")
                        .font(.caption)
                }
                .buttonStyle(.plain)
                .foregroundColor(.magnetarPrimary)
            }
            .padding(8)
            .background(Color.surfaceTertiary.opacity(0.3))
            .cornerRadius(6)
        }
    }

    // MARK: - Helper Functions

    private func checkOllamaStatus() async {
        isCheckingOllama = true

        do {
            let url = URL(string: "http://localhost:11434/api/version")!
            var request = URLRequest(url: url)
            request.timeoutInterval = 3

            let (_, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                await MainActor.run {
                    ollamaServerRunning = httpResponse.statusCode == 200
                    isCheckingOllama = false
                }
            }
        } catch {
            await MainActor.run {
                ollamaServerRunning = false
                isCheckingOllama = false
            }
        }
    }

    private func startOllama() async {
        isCheckingOllama = true

        // Try to start Ollama server
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/local/bin/ollama")
        process.arguments = ["serve"]

        do {
            try process.run()
            // Wait a moment for server to start
            try await Task.sleep(nanoseconds: 3_000_000_000)
            await checkOllamaStatus()
        } catch {
            print("Failed to start Ollama: \(error)")
            isCheckingOllama = false
        }
    }
}

// MARK: - Hub Tab Enum

enum HubTab: String, CaseIterable, Identifiable {
    case localModels
    case cloudModels
    case performance
    case settings

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .localModels: return "Local Models"
        case .cloudModels: return "Cloud Models"
        case .performance: return "Performance"
        case .settings: return "Settings"
        }
    }

    var icon: String {
        switch self {
        case .localModels: return "cube.box"
        case .cloudModels: return "cloud"
        case .performance: return "chart.xyaxis.line"
        case .settings: return "gearshape"
        }
    }

    var shortName: String {
        switch self {
        case .localModels: return "Local"
        case .cloudModels: return "Cloud"
        case .performance: return "Stats"
        case .settings: return "Config"
        }
    }
}

// MARK: - Tag Editor Sheet

struct TagEditorSheet: View {
    let model: OllamaModel
    let onSave: (OllamaModel) -> Void

    @State private var selectedTags: Set<String> = []
    @State private var availableTags: [ModelTag] = []
    @State private var isLoadingTags: Bool = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Edit Capabilities")
                        .font(.title2)
                        .fontWeight(.semibold)

                    Text(model.name)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)

                Button("Save") {
                    // Create updated model with new tags
                    onSave(model)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.return)
            }
            .padding()

            Divider()

            // Tag grid
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Select all capabilities that apply to this model:")
                        .font(.body)
                        .foregroundColor(.secondary)

                    LazyVGrid(columns: [
                        GridItem(.adaptive(minimum: 160, maximum: 200), spacing: 12)
                    ], spacing: 12) {
                        ForEach(availableTags) { tag in
                            tagButton(tag: tag)
                        }
                    }

                    Divider()
                        .padding(.vertical, 8)

                    HStack {
                        Button {
                            // Auto-detect tags for this model
                            autoDetectTags()
                        } label: {
                            Label("Auto-detect from name", systemImage: "sparkles")
                        }
                        .buttonStyle(.bordered)

                        Spacer()

                        Text("\(selectedTags.count) capabilities selected")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding()
            }
        }
        .frame(width: 600, height: 500)
        .task {
            loadAvailableTags()
            // Initialize selected tags from model
            if let tags = model.tags {
                selectedTags = Set(tags)
            }
        }
    }

    @ViewBuilder
    private func tagButton(tag: ModelTag) -> some View {
        let isSelected = selectedTags.contains(tag.id)

        Button {
            if isSelected {
                selectedTags.remove(tag.id)
            } else {
                selectedTags.insert(tag.id)
            }
        } label: {
            HStack(spacing: 8) {
                Text(tag.icon)
                    .font(.title3)

                VStack(alignment: .leading, spacing: 2) {
                    Text(tag.name)
                        .font(.subheadline)
                        .fontWeight(.medium)

                    Text(tag.description)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.magnetarPrimary)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity)
            .background(isSelected ? Color.magnetarPrimary.opacity(0.15) : Color.surfaceSecondary.opacity(0.5))
            .cornerRadius(8)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.magnetarPrimary : Color.surfaceTertiary.opacity(0.3), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func loadAvailableTags() {
        isLoadingTags = true

        Task {
            do {
                // Fetch all available tags from backend
                let url = URL(string: "http://localhost:8000/api/v1/chat/models/tags")!
                var request = URLRequest(url: url)
                request.httpMethod = "GET"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")

                let (data, _) = try await URLSession.shared.data(for: request)
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let tags = try decoder.decode([ModelTag].self, from: data)

                await MainActor.run {
                    self.availableTags = tags
                    self.isLoadingTags = false
                }
            } catch {
                print("Failed to load tags: \(error)")
                await MainActor.run {
                    self.isLoadingTags = false
                }
            }
        }
    }

    private func autoDetectTags() {
        // Call backend to auto-detect tags from model name
        // For now, just use the tags that came with the model
        if let tags = model.tags {
            selectedTags = Set(tags)
        }
    }
}

// MARK: - MagnetarHub Sidebar

struct MagnetarHubSidebar: View {
    @State private var selectedTab: HubTab = .localModels
    @State private var ollamaServerRunning: Bool = false
    @State private var isCloudAuthenticated: Bool = false
    @State private var isCheckingOllama: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("MagnetarHub")
                    .font(.headline)

                Spacer()
            }
            .padding()

            Divider()

            // Tab selection
            List(HubTab.allCases, selection: $selectedTab) { tab in
                Label(tab.displayName, systemImage: tab.icon)
                    .tag(tab)
            }
            .listStyle(.sidebar)
            .frame(height: 200)

            Divider()

            // System Status
            systemStatusPanel
                .padding(12)

            Spacer()
        }
        .task {
            await checkOllamaStatus()
        }
    }

    private var systemStatusPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("System Status")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)

            // Ollama Server Status
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
            }
            .padding(8)
            .background(Color.surfaceTertiary.opacity(0.3))
            .cornerRadius(6)

            // MagnetarCloud Status
            HStack(spacing: 8) {
                Circle()
                    .fill(isCloudAuthenticated ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)

                VStack(alignment: .leading, spacing: 2) {
                    Text("MagnetarCloud")
                        .font(.caption)
                        .fontWeight(.medium)

                    Text(isCloudAuthenticated ? "Connected" : "Not connected")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(8)
            .background(Color.surfaceTertiary.opacity(0.3))
            .cornerRadius(6)
        }
    }

    private func checkOllamaStatus() async {
        isCheckingOllama = true

        do {
            let url = URL(string: "http://localhost:11434/api/version")!
            var request = URLRequest(url: url)
            request.timeoutInterval = 3

            let (_, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                await MainActor.run {
                    ollamaServerRunning = httpResponse.statusCode == 200
                    isCheckingOllama = false
                }
            }
        } catch {
            await MainActor.run {
                ollamaServerRunning = false
                isCheckingOllama = false
            }
        }
    }
}

// MARK: - Preview

#Preview {
    MagnetarHubWorkspace()
        .environment(UserStore())
        .frame(width: 1200, height: 800)
}
