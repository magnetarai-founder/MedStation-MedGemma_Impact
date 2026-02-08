//
//  HubModels.swift
//  MagnetarStudio (macOS)
//
//  Data models and supporting types for MagnetarHub
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HubModels")

// MARK: - Hub Category

enum HubCategory: String, CaseIterable, Identifiable {
    case myModels = "my_models"
    case discover = "discover"
    case huggingface = "huggingface"
    case cloud = "cloud"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .myModels: return "My Models"
        case .discover: return "Discover"
        case .huggingface: return "HuggingFace"
        case .cloud: return "Cloud Models"
        }
    }

    var description: String {
        switch self {
        case .myModels: return "Installed local models"
        case .discover: return "Browse Ollama library"
        case .huggingface: return "GGUF models for llama.cpp"
        case .cloud: return "MagnetarCloud models"
        }
    }

    var icon: String {
        switch self {
        case .myModels: return "cube.box"
        case .discover: return "magnifyingglass"
        case .huggingface: return "face.smiling"
        case .cloud: return "cloud"
        }
    }

    var emptyIcon: String {
        switch self {
        case .myModels: return "cube.box"
        case .discover: return "magnifyingglass.circle"
        case .huggingface: return "face.smiling"
        case .cloud: return "cloud"
        }
    }

    var emptyTitle: String {
        switch self {
        case .myModels: return "No Models Installed"
        case .discover: return "No Models Found"
        case .huggingface: return "No GGUF Models"
        case .cloud: return "Not Connected"
        }
    }

    var emptySubtitle: String {
        switch self {
        case .myModels: return "Download models from Discover tab"
        case .discover: return "Try a different search"
        case .huggingface: return "Download GGUF models for llama.cpp"
        case .cloud: return "Sign in to MagnetarCloud"
        }
    }
}

// MARK: - AnyModelItem (Type-erased model)

enum AnyModelItem: Identifiable {
    case local(OllamaModel)
    case backendRecommended(BackendRecommendedModel)
    case huggingface(HuggingFaceModel)
    case cloud(OllamaModel)

    var id: String {
        switch self {
        case .local(let model): return "local-\(model.id)"
        case .backendRecommended(let model): return "recommended-\(model.id)"
        case .huggingface(let model): return "hf-\(model.id)"
        case .cloud(let model): return "cloud-\(model.id)"
        }
    }

    var name: String {
        switch self {
        case .local(let model): return model.name
        case .backendRecommended(let model): return model.modelName
        case .huggingface(let model): return model.name
        case .cloud(let model): return model.name
        }
    }

    var displayName: String {
        switch self {
        case .local(let model): return model.name
        case .backendRecommended(let model): return model.displayName
        case .huggingface(let model): return model.name
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
        case .huggingface(let model): return model.description
        case .cloud: return nil
        }
    }

    var icon: String {
        switch self {
        case .local: return "cube.box.fill"
        case .backendRecommended: return "star.circle.fill"
        case .huggingface: return "face.smiling.fill"
        case .cloud: return "cloud.fill"
        }
    }

    var iconGradient: LinearGradient {
        switch self {
        case .local: return LinearGradient.magnetarGradient
        case .backendRecommended:
            return LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .huggingface:
            return LinearGradient(colors: [.yellow, .orange], startPoint: .topLeading, endPoint: .bottomTrailing)
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
        case .huggingface(let model):
            var badges = model.capabilities
            if model.isDownloaded {
                badges.insert("installed", at: 0)
            }
            badges.append(model.quantization)
            return badges
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
        case "medical": return .red
        case "code": return .cyan
        case "vision": return .indigo
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
        case .huggingface(let model): return model.parameterCount
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
        case .huggingface(let model): return model.capabilities.count > 1
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
        case .huggingface(let model): return model.capabilities
        case .cloud: return []
        }
    }

    var stat1: (icon: String, text: String)? {
        switch self {
        case .local(let model):
            return ("internaldrive", model.sizeFormatted)
        case .backendRecommended(let model):
            return ("tag", model.parameterSize)
        case .huggingface(let model):
            return ("internaldrive", model.sizeFormatted)
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
        case .huggingface(let model):
            if model.capabilities.contains("medical") {
                return ("cross.case.fill", "Medical")
            } else if model.capabilities.contains("code") {
                return ("chevron.left.forwardslash.chevron.right", "Code")
            } else {
                return ("cpu", "llama.cpp")
            }
        case .cloud: return nil
        }
    }

    func detailActions(
        activeDownloads: Binding<[String: LegacyDownloadProgress]>,
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
                                .foregroundStyle(.secondary)
                            Text("Size: \(model.sizeFormatted)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
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
                                    .foregroundStyle(progress.error != nil ? .red : .secondary)
                                Spacer()
                                if progress.error == nil {
                                    Text("\(Int(progress.progress * 100))%")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
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

            case .huggingface(let model):
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.isDownloaded ? "Actions" : "Download")
                        .font(.headline)

                    if model.isDownloaded {
                        HStack(spacing: 12) {
                            Button {
                                onDelete(model.id)
                            } label: {
                                Label("Delete", systemImage: "trash")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.bordered)
                            .tint(.red)

                            Button {
                                // Start llama.cpp with this model
                                Task {
                                    do {
                                        _ = try await LlamaCppService.shared.startServer(modelId: model.id)
                                    } catch {
                                        logger.error("Failed to start llama.cpp for model \(model.id): \(error)")
                                    }
                                }
                            } label: {
                                Label("Run", systemImage: "play.fill")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    } else {
                        if let progress = activeDownloads.wrappedValue[model.id] {
                            // Show progress
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(progress.status)
                                        .font(.caption)
                                        .foregroundStyle(progress.error != nil ? .red : .secondary)
                                    Spacer()
                                    if progress.error == nil {
                                        Text("\(Int(progress.progress * 100))%")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
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
                                onDownload(model.id)
                            } label: {
                                Label("Download \(model.name)", systemImage: "arrow.down.circle")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    }

                    // Hardware requirements
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Image(systemName: "memorychip")
                                .foregroundStyle(.secondary)
                            Text("Min VRAM: \(String(format: "%.1f", model.minVramGb)) GB")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        HStack {
                            Image(systemName: "cpu")
                                .foregroundStyle(.secondary)
                            Text("Quantization: \(model.quantization)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

            case .cloud:
                VStack(alignment: .leading, spacing: 12) {
                    Text("Cloud Actions")
                        .font(.headline)

                    Button {
                        // Trigger cloud sync via VaultStore (Tier 15 implementation)
                        Task {
                            logger.info("Sync to Local triggered")
                            await VaultStore.shared.syncFromCloud()
                        }
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
                                .foregroundStyle(Color.magnetarPrimary)
                            Text("Multi-Purpose: \(metadata.primaryUseCases.joined(separator: ", "))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                                .font(.caption)
                                .foregroundStyle(Color.magnetarPrimary)
                            Text("Capability: \(metadata.capability.capitalized)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    // Parameter size
                    if let paramSize = metadata.parameterSize {
                        HStack(spacing: 6) {
                            Image(systemName: "tag")
                                .font(.caption)
                                .foregroundStyle(Color.magnetarPrimary)
                            Text("Size: \(paramSize)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    // Strengths
                    if !metadata.strengths.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Strengths:")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundStyle(.secondary)
                            ForEach(metadata.strengths, id: \.self) { strength in
                                HStack(spacing: 4) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.caption2)
                                        .foregroundStyle(.green)
                                    Text(strength)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
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
                                .foregroundStyle(.secondary)
                            Text(metadata.idealFor)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.top, 4)
                    }
                } else {
                    // Fallback: basic model info
                    if let family = model.details?.family {
                        HStack {
                            Text("Family:")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(family)
                                .font(.caption)
                        }
                    }

                    if let digest = model.digest {
                        HStack {
                            Text("Digest:")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(digest.prefix(12))
                                .font(.caption2)
                                .foregroundStyle(.secondary)
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
                            .foregroundStyle(Color.magnetarPrimary)
                        Text("Multi-Purpose: \(model.primaryUseCases.joined(separator: ", "))")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    HStack(spacing: 6) {
                        Image(systemName: "sparkles")
                            .font(.caption)
                            .foregroundStyle(Color.magnetarPrimary)
                        Text("Capability: \(model.capability.capitalized)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                HStack(spacing: 6) {
                    Image(systemName: "tag")
                        .font(.caption)
                        .foregroundStyle(Color.magnetarPrimary)
                    Text("Size: \(model.parameterSize)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

        case .huggingface(let model):
            VStack(alignment: .leading, spacing: 8) {
                Text("About")
                    .font(.headline)

                // Capabilities
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.caption)
                        .foregroundStyle(Color.magnetarPrimary)
                    Text("Capabilities: \(model.capabilities.joined(separator: ", "))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                // Parameter size
                HStack(spacing: 6) {
                    Image(systemName: "tag")
                        .font(.caption)
                        .foregroundStyle(Color.magnetarPrimary)
                    Text("Parameters: \(model.parameterCount)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                // Quantization
                HStack(spacing: 6) {
                    Image(systemName: "square.stack.3d.up")
                        .font(.caption)
                        .foregroundStyle(Color.magnetarPrimary)
                    Text("Quantization: \(model.quantization)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                // Context length
                HStack(spacing: 6) {
                    Image(systemName: "text.alignleft")
                        .font(.caption)
                        .foregroundStyle(Color.magnetarPrimary)
                    Text("Context: \(model.contextLength) tokens")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                // Hardware requirements
                VStack(alignment: .leading, spacing: 4) {
                    Text("Hardware Requirements:")
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundStyle(.secondary)
                    HStack(spacing: 4) {
                        Image(systemName: "memorychip")
                            .font(.caption2)
                            .foregroundStyle(.orange)
                        Text("Min VRAM: \(String(format: "%.1f", model.minVramGb)) GB")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    HStack(spacing: 4) {
                        Image(systemName: "memorychip.fill")
                            .font(.caption2)
                            .foregroundStyle(.green)
                        Text("Recommended: \(String(format: "%.1f", model.recommendedVramGb)) GB")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.top, 4)
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

// MARK: - Download Progress (Legacy)

/// Legacy download progress - prefer HuggingFaceService.DownloadProgress for new code
struct LegacyDownloadProgress {
    let modelName: String
    let status: String
    let progress: Double
    var error: String? = nil
}
