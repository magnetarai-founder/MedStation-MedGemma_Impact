//
//  MagnetarHubWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Model management workspace with uniform three-pane Outlook-style layout.
//

import SwiftUI

struct MagnetarHubWorkspace: View {
    @State private var modelsStore = ModelsStore()
    @State private var selectedCategory: ModelCategory? = .all
    @State private var selectedModel: OllamaModel? = nil
    @State private var ollamaServerRunning: Bool = false
    @State private var isCloudAuthenticated: Bool = false

    var body: some View {
        ThreePaneLayout {
            // Left Pane: Model Categories
            categoryListPane
        } middlePane: {
            // Middle Pane: Model List
            modelListPane
        } rightPane: {
            // Right Pane: Model Detail
            modelDetailPane
        }
        .task {
            await checkOllamaStatus()
            await modelsStore.fetchModels()
        }
    }

    // MARK: - Left Pane: Categories

    private var categoryListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "MagnetarHub",
                icon: "cube.box"
            )

            Divider()

            List(ModelCategory.allCases, selection: $selectedCategory) { category in
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
                .tag(category)
            }
            .listStyle(.sidebar)

            Divider()

            // System Status
            systemStatusSection
                .padding(12)
        }
    }

    private var systemStatusSection: some View {
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

    // MARK: - Middle Pane: Model List

    private var modelListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: selectedCategory?.displayName ?? "Models",
                subtitle: "\(filteredModels.count) models",
                action: {
                    Task {
                        await modelsStore.fetchModels()
                    }
                },
                actionIcon: "arrow.clockwise"
            )

            Divider()

            if modelsStore.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredModels.isEmpty {
                PaneEmptyState(
                    icon: "cube.box",
                    title: "No models found",
                    subtitle: "Pull a model from Ollama to get started"
                )
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(filteredModels) { model in
                            ModelRow(model: model, isSelected: selectedModel?.id == model.id)
                                .onTapGesture {
                                    selectedModel = model
                                }
                        }
                    }
                }
            }
        }
    }

    private var filteredModels: [OllamaModel] {
        guard let category = selectedCategory else { return modelsStore.models }

        switch category {
        case .all:
            return modelsStore.models
        case .code:
            return modelsStore.models.filter { model in
                model.tags?.contains("code") == true
            }
        case .chat:
            return modelsStore.models.filter { model in
                model.tags?.contains("chat") == true
            }
        case .vision:
            return modelsStore.models.filter { model in
                model.tags?.contains("vision") == true
            }
        case .reasoning:
            return modelsStore.models.filter { model in
                model.tags?.contains("reasoning") == true
            }
        case .cloud:
            return [] // TODO: Fetch cloud models
        }
    }

    // MARK: - Right Pane: Model Detail

    private var modelDetailPane: some View {
        Group {
            if let model = selectedModel {
                VStack(spacing: 0) {
                    // Model header
                    HStack(spacing: 16) {
                        Image(systemName: "cube.box.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        VStack(alignment: .leading, spacing: 6) {
                            Text(model.name)
                                .font(.title2)
                                .fontWeight(.bold)

                            HStack(spacing: 8) {
                                HStack(spacing: 4) {
                                    Image(systemName: "circle.fill")
                                        .font(.caption2)
                                        .foregroundColor(.green)
                                    Text("Installed")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                Text("•")
                                    .foregroundColor(.secondary)

                                Text(model.size)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            // Capability tags
                            if let tagDetails = model.tagDetails, !tagDetails.isEmpty {
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 6) {
                                        ForEach(tagDetails) { tag in
                                            CapabilityTagBadge(tag: tag)
                                        }
                                    }
                                }
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
                            // Actions
                            HStack(spacing: 12) {
                                Button(action: {
                                    // TODO: Use model in chat
                                }) {
                                    Label("Use in Chat", systemImage: "bubble.left")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.borderedProminent)

                                Button(action: {
                                    // TODO: Update model
                                }) {
                                    Label("Update", systemImage: "arrow.down.circle")
                                        .frame(maxWidth: .infinity)
                                }
                                .buttonStyle(.bordered)

                                Button(action: {
                                    // TODO: Delete model
                                }) {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.bordered)
                                .foregroundColor(.red)
                            }

                            Divider()

                            // Model info
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Model Information")
                                    .font(.headline)

                                if let digest = model.digest {
                                    DetailRow(icon: "number", label: "Digest", value: String(digest.prefix(16)) + "...")
                                }

                                DetailRow(icon: "calendar", label: "Modified", value: model.modifiedAt)

                                DetailRow(icon: "externaldrive", label: "Size", value: model.size)
                            }

                            Divider()

                            // Capabilities
                            if let tagDetails = model.tagDetails, !tagDetails.isEmpty {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("Capabilities")
                                        .font(.headline)

                                    ForEach(tagDetails) { tag in
                                        HStack(spacing: 12) {
                                            Image(systemName: tag.icon)
                                                .foregroundStyle(LinearGradient.magnetarGradient)
                                                .frame(width: 24)

                                            VStack(alignment: .leading, spacing: 2) {
                                                Text(tag.name)
                                                    .font(.body)
                                                    .fontWeight(.medium)
                                                Text(tag.description)
                                                    .font(.caption)
                                                    .foregroundColor(.secondary)
                                            }
                                        }
                                        .padding(12)
                                        .background(Color.surfaceSecondary.opacity(0.3))
                                        .cornerRadius(8)
                                    }
                                }
                            }

                            Spacer()
                        }
                        .padding(24)
                    }
                }
            } else {
                PaneEmptyState(
                    icon: "cube.box",
                    title: "No model selected",
                    subtitle: "Select a model to view details and actions"
                )
            }
        }
    }

    // MARK: - Helper Functions

    private func checkOllamaStatus() async {
        do {
            let url = URL(string: "http://localhost:11434/api/version")!
            var request = URLRequest(url: url)
            request.timeoutInterval = 3

            let (_, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                await MainActor.run {
                    ollamaServerRunning = httpResponse.statusCode == 200
                }
            }
        } catch {
            await MainActor.run {
                ollamaServerRunning = false
            }
        }
    }
}

// MARK: - Supporting Views

struct ModelRow: View {
    let model: OllamaModel
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "cube.box.fill")
                .font(.title3)
                .foregroundStyle(LinearGradient.magnetarGradient)

            VStack(alignment: .leading, spacing: 4) {
                Text(model.name)
                    .font(.headline)
                    .foregroundColor(.textPrimary)

                // Capability tags in row
                if let tagDetails = model.tagDetails, !tagDetails.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 4) {
                            ForEach(tagDetails.prefix(3)) { tag in
                                CapabilityTagBadge(tag: tag, compact: true)
                            }
                            if tagDetails.count > 3 {
                                Text("+\(tagDetails.count - 3)")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                } else {
                    Text(model.size)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()
        }
        .padding(12)
        .background(isSelected ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
        .cornerRadius(8)
    }
}

struct CapabilityTagBadge: View {
    let tag: ModelTag
    var compact: Bool = false

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: tag.icon)
                .font(.caption2)
            if !compact {
                Text(tag.name)
                    .font(.caption2)
            }
        }
        .fontWeight(.semibold)
        .padding(.horizontal, compact ? 6 : 8)
        .padding(.vertical, 4)
        .background(tagColor.opacity(0.2))
        .foregroundColor(tagColor)
        .cornerRadius(6)
    }

    private var tagColor: Color {
        // Map tag IDs to colors
        switch tag.id {
        case "code": return .blue
        case "chat": return .purple
        case "vision": return .orange
        case "reasoning": return .green
        case "multilingual": return .pink
        case "function_calling": return .cyan
        case "json_mode": return .indigo
        default: return .gray
        }
    }
}

// MARK: - Models

enum ModelCategory: String, CaseIterable, Identifiable {
    case all = "all"
    case code = "code"
    case chat = "chat"
    case vision = "vision"
    case reasoning = "reasoning"
    case cloud = "cloud"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .all: return "All Models"
        case .code: return "Code Models"
        case .chat: return "Chat Models"
        case .vision: return "Vision Models"
        case .reasoning: return "Reasoning Models"
        case .cloud: return "Cloud Models"
        }
    }

    var description: String {
        switch self {
        case .all: return "All local models"
        case .code: return "Code generation & analysis"
        case .chat: return "Conversational AI"
        case .vision: return "Image understanding"
        case .reasoning: return "Complex problem solving"
        case .cloud: return "MagnetarCloud models"
        }
    }

    var icon: String {
        switch self {
        case .all: return "cube.box"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .chat: return "bubble.left"
        case .vision: return "eye"
        case .reasoning: return "brain"
        case .cloud: return "cloud"
        }
    }
}

// MARK: - Preview

#Preview {
    MagnetarHubWorkspace()
        .frame(width: 1200, height: 800)
}
