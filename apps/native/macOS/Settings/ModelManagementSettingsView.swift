//
//  ModelManagementSettingsView.swift
//  MagnetarStudio
//
//  Settings panel for model management and configuration.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ModelManagementSettingsView")

// MARK: - Model Management Settings

struct ModelManagementSettingsView: View {
    // Intelligent Routing
    @AppStorage("enableAppleFM") private var enableAppleFM = true
    @AppStorage("orchestratorModel") private var orchestratorModel = "apple_fm"

    // Default Model Parameters
    @AppStorage("defaultTemperature") private var defaultTemperature = 0.7
    @AppStorage("defaultTopP") private var defaultTopP = 0.9
    @AppStorage("defaultTopK") private var defaultTopK = 40
    @AppStorage("defaultRepeatPenalty") private var defaultRepeatPenalty = 1.1

    // Model Behavior Presets
    @AppStorage("modelPreset") private var modelPreset = "balanced"

    // Global Prompts
    @AppStorage("globalSystemPrompt") private var globalSystemPrompt = ""
    @AppStorage("enableGlobalPrompt") private var enableGlobalPrompt = false

    // Model Routing Rules
    @AppStorage("dataQueryModel") private var dataQueryModel = "sqlcoder:7b"
    @AppStorage("chatModel") private var chatModel = "llama3.2:3b"
    @AppStorage("codeModel") private var codeModel = "qwen2.5-coder:3b"

    @State private var availableModels: [String] = []
    @State private var orchestratorModels: [OllamaModelWithTags] = []
    @State private var isLoadingModels: Bool = false

    var body: some View {
        Form {
            // Intelligent Routing Section
            Section("Intelligent Routing (Apple FM)") {
                Toggle("Enable Intelligent Model Router", isOn: $enableAppleFM)
                    .help("Automatically selects the best model based on query type")

                if enableAppleFM {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Orchestrator Model")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        if isLoadingModels {
                            HStack(spacing: 8) {
                                ProgressView()
                                    .controlSize(.small)
                                Text("Loading orchestrator-capable models...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 4)
                        } else {
                            Picker("", selection: $orchestratorModel) {
                                // Apple FM option (default)
                                Text("Apple FM (Intelligent Router)")
                                    .tag("apple_fm")

                                if !orchestratorModels.isEmpty {
                                    Divider()

                                    // Models tagged with "orchestration" capability
                                    ForEach(orchestratorModels, id: \.name) { model in
                                        Text(model.name)
                                            .tag(model.name)
                                    }
                                }
                            }
                            .labelsHidden()
                            .disabled(orchestratorModels.isEmpty && orchestratorModel != "apple_fm")
                        }

                        if orchestratorModel == "apple_fm" {
                            Text("Apple FM analyzes your query and intelligently routes to the best model")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Using \(orchestratorModel) as the orchestrator for all queries")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            // Model Behavior Presets
            Section("Default Behavior") {
                Picker("Preset", selection: $modelPreset) {
                    Text("Creative").tag("creative")
                    Text("Balanced").tag("balanced")
                    Text("Precise").tag("precise")
                    Text("Custom").tag("custom")
                }
                .onChange(of: modelPreset) { _, newValue in
                    applyPreset(newValue)
                }

                if modelPreset == "custom" {
                    VStack(alignment: .leading, spacing: 12) {
                        // Temperature
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Temperature")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultTemperature))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultTemperature, in: 0...2, step: 0.1)
                        }

                        // Top P
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Top P")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultTopP))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultTopP, in: 0...1, step: 0.05)
                        }

                        // Top K
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Top K")
                                    .font(.caption)
                                Spacer()
                                Text("\(defaultTopK)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: Binding(
                                get: { Double(defaultTopK) },
                                set: { defaultTopK = Int($0) }
                            ), in: 1...100, step: 1)
                        }

                        // Repeat Penalty
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Repeat Penalty")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultRepeatPenalty))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultRepeatPenalty, in: 1...2, step: 0.1)
                        }
                    }
                }
            }

            // Model Routing Rules
            Section("Model Routing Rules") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Data Queries")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $dataQueryModel) {
                        Text("sqlcoder:7b").tag("sqlcoder:7b")
                        Text("qwen2.5-coder:3b").tag("qwen2.5-coder:3b")
                    }
                    .labelsHidden()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("General Chat")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $chatModel) {
                        Text("llama3.2:3b").tag("llama3.2:3b")
                        Text("phi3.5:3.8b").tag("phi3.5:3.8b")
                        Text("magnetar32:3b").tag("magnetar32:3b")
                    }
                    .labelsHidden()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Code Generation")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $codeModel) {
                        Text("qwen2.5-coder:3b").tag("qwen2.5-coder:3b")
                        Text("qwen3-coder:30b").tag("qwen3-coder:30b")
                        Text("deepseek-r1:8b").tag("deepseek-r1:8b")
                    }
                    .labelsHidden()
                }
            }

            // Global System Prompt
            Section("Global System Prompt") {
                Toggle("Enable Global Prompt", isOn: $enableGlobalPrompt)
                    .help("Applies this prompt to all model conversations")

                if enableGlobalPrompt {
                    VStack(alignment: .leading, spacing: 8) {
                        TextEditor(text: $globalSystemPrompt)
                            .frame(height: 100)
                            .font(.system(size: 12, design: .monospaced))
                            .padding(4)
                            .background(Color.surfaceSecondary)
                            .cornerRadius(6)

                        Text("This prompt will be prepended to all conversations")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .task {
            await loadAvailableModels()
        }
    }

    private func applyPreset(_ preset: String) {
        switch preset {
        case "creative":
            defaultTemperature = 1.2
            defaultTopP = 0.95
            defaultTopK = 50
            defaultRepeatPenalty = 1.0
        case "balanced":
            defaultTemperature = 0.7
            defaultTopP = 0.9
            defaultTopK = 40
            defaultRepeatPenalty = 1.1
        case "precise":
            defaultTemperature = 0.3
            defaultTopP = 0.85
            defaultTopK = 20
            defaultRepeatPenalty = 1.2
        default:
            break
        }
    }

    private func loadAvailableModels() async {
        await MainActor.run {
            isLoadingModels = true
        }

        do {
            // Load models with tags
            let url = URL(string: "\(APIConfiguration.shared.chatModelsURL)/with-tags")!
            let (data, _) = try await URLSession.shared.data(from: url)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let models = try decoder.decode([OllamaModelWithTags].self, from: data)

            // Filter for orchestration-capable models
            let orchestrators = models.filter { model in
                model.tags.contains("orchestration")
            }

            await MainActor.run {
                self.orchestratorModels = orchestrators
                self.availableModels = models.map { $0.name }
                self.isLoadingModels = false
            }
        } catch {
            logger.error("Failed to load models: \(error)")
            await MainActor.run {
                self.isLoadingModels = false
            }
        }
    }
}

// MARK: - Supporting Models

struct OllamaModelWithTags: Codable, Identifiable {
    let id: String
    let name: String
    let size: Int64
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case id, name, size, tags
    }
}
