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
    @State private var cloudModels: [OllamaModel] = []
    @State private var isLoadingCloudModels: Bool = false
    @State private var cloudError: String? = nil
    @State private var isPerformingAction: Bool = false
    @State private var actionMessage: String? = nil
    @State private var showDeleteConfirmation: Bool = false

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
            await checkCloudAuthStatus()
            await modelsStore.fetchModels()
            await fetchCloudModels()
        }
        .alert("Delete Model", isPresented: $showDeleteConfirmation, presenting: selectedModel) { model in
            Button("Cancel", role: .cancel) {
                showDeleteConfirmation = false
            }
            Button("Delete", role: .destructive) {
                Task {
                    await deleteCloudModel(model.id)
                }
                showDeleteConfirmation = false
            }
        } message: { model in
            Text("Are you sure you want to delete '\(model.name)' from MagnetarCloud?")
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
                        if selectedCategory == .cloud {
                            await fetchCloudModels()
                        } else {
                            await modelsStore.fetchModels()
                        }
                    }
                },
                actionIcon: "arrow.clockwise"
            )

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = currentError {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)

                    Text("Error Loading Models")
                        .font(.headline)

                    Text(error)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)

                    Button("Retry") {
                        Task {
                            if selectedCategory == .cloud {
                                await fetchCloudModels()
                            } else {
                                await modelsStore.fetchModels()
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredModels.isEmpty {
                PaneEmptyState(
                    icon: selectedCategory == .cloud ? "cloud" : "cube.box",
                    title: "No models found",
                    subtitle: selectedCategory == .cloud ? "No cloud models available" : "Pull a model from Ollama to get started"
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

    private var isLoading: Bool {
        selectedCategory == .cloud ? isLoadingCloudModels : modelsStore.isLoading
    }

    private var currentError: String? {
        selectedCategory == .cloud ? cloudError : nil
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
            return cloudModels
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
                                    Task {
                                        await useCloudModel(model.id)
                                    }
                                }) {
                                    if isPerformingAction {
                                        ProgressView()
                                            .scaleEffect(0.8)
                                            .frame(maxWidth: .infinity)
                                    } else {
                                        Label("Use in Chat", systemImage: "bubble.left")
                                            .frame(maxWidth: .infinity)
                                    }
                                }
                                .buttonStyle(.borderedProminent)
                                .disabled(isPerformingAction || selectedCategory != .cloud)

                                Button(action: {
                                    Task {
                                        await updateCloudModel(model.id)
                                    }
                                }) {
                                    if isPerformingAction {
                                        ProgressView()
                                            .scaleEffect(0.8)
                                            .frame(maxWidth: .infinity)
                                    } else {
                                        Label("Update", systemImage: "arrow.down.circle")
                                            .frame(maxWidth: .infinity)
                                    }
                                }
                                .buttonStyle(.bordered)
                                .disabled(isPerformingAction || selectedCategory != .cloud)

                                Button(action: {
                                    showDeleteConfirmation = true
                                }) {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.bordered)
                                .foregroundColor(.red)
                                .disabled(isPerformingAction || selectedCategory != .cloud)
                            }

                            // Action message (success/error feedback)
                            if let message = actionMessage {
                                HStack(spacing: 8) {
                                    Image(systemName: message.hasPrefix("Error") ? "exclamationmark.circle" : "checkmark.circle")
                                        .foregroundColor(message.hasPrefix("Error") ? .red : .green)

                                    Text(message)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                .padding(8)
                                .background(Color.surfaceSecondary.opacity(0.5))
                                .cornerRadius(6)
                            }

                            Divider()

                            // Model info
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Model Information")
                                    .font(.headline)

                                if let digest = model.digest {
                                    DetailRow(icon: "number", label: "Digest", value: String(digest.prefix(16)) + "...")
                                }

                                if let modifiedAt = model.modifiedAt {
                                    DetailRow(icon: "calendar", label: "Modified", value: modifiedAt)
                                }

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

    // MARK: - Cloud Auth Status

    @MainActor
    private func checkCloudAuthStatus() async {
        // Check if user is authenticated with MagnetarCloud
        if let token = KeychainService.shared.loadToken(), !token.isEmpty {
            isCloudAuthenticated = true
        } else {
            isCloudAuthenticated = false
        }
    }

    // MARK: - Cloud Models CRUD

    @MainActor
    private func fetchCloudModels() async {
        isLoadingCloudModels = true
        cloudError = nil

        do {
            let url = URL(string: "http://localhost:8000/api/v1/cloud/models")!
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (data, response) = try await URLSession.shared.data(for: request)

            // Handle 404 gracefully (endpoint not yet implemented)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw URLError(.badServerResponse)
            }

            if httpResponse.statusCode == 404 {
                // Cloud models endpoint not yet implemented - use empty list
                cloudModels = []
                isLoadingCloudModels = false
                return
            } else if httpResponse.statusCode == 200 {
                // Parse cloud models (same format as OllamaModel)
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                cloudModels = try decoder.decode([OllamaModel].self, from: data)
            } else if httpResponse.statusCode == 401 {
                cloudError = "Not authenticated. Please sign in to MagnetarCloud."
                isCloudAuthenticated = false
                cloudModels = []
            } else {
                cloudError = "Failed to load cloud models: HTTP \(httpResponse.statusCode)"
                cloudModels = []
            }

        } catch let error as URLError {
            cloudError = "Network error: \(error.localizedDescription)"
            cloudModels = []
        } catch {
            cloudError = "Failed to load cloud models: \(error.localizedDescription)"
            cloudModels = []
        }

        isLoadingCloudModels = false
    }

    @MainActor
    private func useCloudModel(_ modelId: String) async {
        isPerformingAction = true
        actionMessage = nil

        do {
            let url = URL(string: "http://localhost:8000/api/v1/cloud/models/\(modelId)/use")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw CloudError.invalidResponse
            }

            if httpResponse.statusCode == 200 {
                actionMessage = "Model activated for chat use"
                // Clear message after 3 seconds
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                actionMessage = nil
            } else {
                actionMessage = "Error: Failed to activate model (HTTP \(httpResponse.statusCode))"
            }

        } catch {
            actionMessage = "Error: \(error.localizedDescription)"
        }

        isPerformingAction = false
    }

    @MainActor
    private func updateCloudModel(_ modelId: String) async {
        isPerformingAction = true
        actionMessage = nil

        // Store original model in case we need to rollback
        let originalModel = cloudModels.first { $0.id == modelId }

        do {
            let url = URL(string: "http://localhost:8000/api/v1/cloud/models/\(modelId)")!
            var request = URLRequest(url: url)
            request.httpMethod = "PUT"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw CloudError.invalidResponse
            }

            if httpResponse.statusCode == 200 {
                // Parse updated model
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let updatedModel = try decoder.decode(OllamaModel.self, from: data)

                // Update in cloudModels array
                if let index = cloudModels.firstIndex(where: { $0.id == modelId }) {
                    cloudModels[index] = updatedModel
                    selectedModel = updatedModel
                }

                actionMessage = "Model updated successfully"
                // Clear message after 3 seconds
                try? await Task.sleep(nanoseconds: 3_000_000_000)
                actionMessage = nil
            } else {
                // Rollback on failure
                if let original = originalModel,
                   let index = cloudModels.firstIndex(where: { $0.id == modelId }) {
                    cloudModels[index] = original
                }
                actionMessage = "Error: Failed to update model (HTTP \(httpResponse.statusCode))"
            }

        } catch {
            // Rollback on failure
            if let original = originalModel,
               let index = cloudModels.firstIndex(where: { $0.id == modelId }) {
                cloudModels[index] = original
            }
            actionMessage = "Error: \(error.localizedDescription)"
        }

        isPerformingAction = false
    }

    @MainActor
    private func deleteCloudModel(_ modelId: String) async {
        // Store original models in case we need to rollback
        let originalModels = cloudModels

        // Optimistic delete
        cloudModels.removeAll { $0.id == modelId }

        // Clear selection if deleted model was selected
        if selectedModel?.id == modelId {
            selectedModel = nil
        }

        do {
            let url = URL(string: "http://localhost:8000/api/v1/cloud/models/\(modelId)")!
            var request = URLRequest(url: url)
            request.httpMethod = "DELETE"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw CloudError.invalidResponse
            }

            if httpResponse.statusCode != 200 && httpResponse.statusCode != 204 {
                // Rollback on failure
                cloudModels = originalModels
                cloudError = "Failed to delete model: HTTP \(httpResponse.statusCode)"
            }

        } catch {
            // Rollback on failure
            cloudModels = originalModels
            cloudError = "Failed to delete model: \(error.localizedDescription)"
        }
    }
}

// MARK: - Cloud Errors

enum CloudError: LocalizedError {
    case invalidResponse
    case unauthorized
    case notFound
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Not authenticated with MagnetarCloud"
        case .notFound:
            return "Model not found"
        case .serverError(let code):
            return "Server error (HTTP \(code))"
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
