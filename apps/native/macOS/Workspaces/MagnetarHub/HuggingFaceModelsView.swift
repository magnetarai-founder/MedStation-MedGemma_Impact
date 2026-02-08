//
//  HuggingFaceModelsView.swift
//  MagnetarStudio (macOS)
//
//  Main view for the HuggingFace tab - displays GGUF models with category filters
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HuggingFaceModelsView")

struct HuggingFaceModelsView: View {
    @State private var models: [HuggingFaceModel] = []
    @State private var selectedCategory: ModelCategory? = nil
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var downloadingModels: [String: DownloadProgress] = [:]
    @State private var hardwareInfo: HardwareInfo?
    @State private var searchText = ""

    private let huggingFaceService = HuggingFaceService.shared
    private let llamaCppService = LlamaCppService.shared

    enum ModelCategory: String, CaseIterable, Identifiable {
        case all = "All"
        case medical = "Medical"
        case code = "Code"
        case chat = "Chat"

        var id: String { rawValue }

        var icon: String {
            switch self {
            case .all: return "square.grid.2x2"
            case .medical: return "cross.case.fill"
            case .code: return "chevron.left.forwardslash.chevron.right"
            case .chat: return "message.fill"
            }
        }

        var apiCapability: String? {
            switch self {
            case .all: return nil
            case .medical: return "medical"
            case .code: return "code"
            case .chat: return "chat"
            }
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar with category filters and search
            toolbar
            Divider()

            // Hardware info banner (if model might not fit)
            if let hardware = hardwareInfo, hardware.availableMemoryGb < 8 {
                HardwareWarningBanner(hardware: hardware)
            }

            // Content
            if isLoading && models.isEmpty {
                loadingView
            } else if let error = errorMessage {
                errorView(error)
            } else if filteredModels.isEmpty {
                emptyView
            } else {
                modelsGrid
            }
        }
        .task {
            await loadData()
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 16) {
            // Category pills
            HStack(spacing: 8) {
                ForEach(ModelCategory.allCases) { category in
                    CategoryPill(
                        title: category.rawValue,
                        icon: category.icon,
                        isSelected: selectedCategory == category || (category == .all && selectedCategory == nil),
                        action: {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedCategory = category == .all ? nil : category
                            }
                        }
                    )
                }
            }

            Spacer()

            // Search field
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                    .font(.caption)
                TextField("Search models...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.caption)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.surfaceTertiary.opacity(0.5))
            .cornerRadius(8)
            .frame(width: 200)

            // Refresh button
            Button {
                Task { await loadData() }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            .disabled(isLoading)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Models Grid

    private var modelsGrid: some View {
        ScrollView {
            LazyVGrid(columns: gridColumns, spacing: 20) {
                ForEach(filteredModels) { model in
                    HuggingFaceModelCard(
                        model: model,
                        downloadProgress: downloadingModels[model.id],
                        hardwareInfo: hardwareInfo,
                        onDownload: { downloadModel(model) },
                        onRun: { runModel(model) },
                        onDelete: { deleteModel(model) }
                    )
                }
            }
            .padding(20)
        }
    }

    // MARK: - Loading/Error/Empty States

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Loading models...")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundStyle(.orange)
            Text("Failed to load models")
                .font(.headline)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") {
                Task { await loadData() }
            }
            .buttonStyle(.bordered)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "face.smiling")
                .font(.system(size: 48))
                .foregroundStyle(
                    LinearGradient(colors: [.yellow, .orange], startPoint: .topLeading, endPoint: .bottomTrailing)
                )
            Text("No GGUF Models")
                .font(.headline)
            Text(selectedCategory != nil ? "No models match this category" : "Download GGUF models for llama.cpp")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Computed Properties

    private var gridColumns: [GridItem] {
        [GridItem(.adaptive(minimum: 300, maximum: 360), spacing: 20)]
    }

    private var filteredModels: [HuggingFaceModel] {
        var result = models

        // Filter by category
        if let category = selectedCategory, let capability = category.apiCapability {
            result = result.filter { $0.capabilities.contains(capability) }
        }

        // Filter by search
        if !searchText.isEmpty {
            let query = searchText.lowercased()
            result = result.filter {
                $0.name.lowercased().contains(query) ||
                $0.description.lowercased().contains(query) ||
                $0.capabilities.contains { $0.lowercased().contains(query) }
            }
        }

        return result
    }

    // MARK: - Data Loading

    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            // Load hardware info and models in parallel
            async let hardwareTask = huggingFaceService.getHardwareInfo()
            async let modelsTask = huggingFaceService.listAvailableModels()

            hardwareInfo = try await hardwareTask
            models = try await modelsTask

            logger.info("Loaded \(models.count) HuggingFace models")
        } catch {
            logger.error("Failed to load HuggingFace models: \(error.localizedDescription)")
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Model Actions

    private func downloadModel(_ model: HuggingFaceModel) {
        logger.info("Starting download: \(model.id)")

        Task {
            do {
                for try await progress in huggingFaceService.downloadModel(modelId: model.id) {
                    await MainActor.run {
                        downloadingModels[model.id] = progress
                    }

                    if progress.status == "completed" {
                        _ = await MainActor.run {
                            downloadingModels.removeValue(forKey: model.id)
                        }
                        // Refresh models list to show updated isDownloaded status
                        await loadData()
                    }
                }
            } catch {
                logger.error("Download failed: \(error.localizedDescription)")
                await MainActor.run {
                    downloadingModels[model.id] = DownloadProgress(
                        jobId: "error",
                        status: "failed",
                        progress: 0,
                        downloadedBytes: 0,
                        totalBytes: 0,
                        speedBps: 0,
                        etaSeconds: nil,
                        message: error.localizedDescription,
                        modelId: model.id,
                        error: error.localizedDescription
                    )
                }
            }
        }
    }

    private func runModel(_ model: HuggingFaceModel) {
        logger.info("Starting llama.cpp with model: \(model.id)")

        Task {
            do {
                let _ = try await llamaCppService.startServer(modelId: model.id)
                logger.info("llama.cpp started successfully")
            } catch {
                logger.error("Failed to start llama.cpp: \(error.localizedDescription)")
            }
        }
    }

    private func deleteModel(_ model: HuggingFaceModel) {
        logger.info("Deleting model: \(model.id)")

        Task {
            do {
                try await huggingFaceService.deleteModel(modelId: model.id)
                await loadData()
            } catch {
                logger.error("Failed to delete model: \(error.localizedDescription)")
            }
        }
    }
}

// MARK: - Category Pill

struct CategoryPill: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption2)
                Text(title)
                    .font(.caption)
                    .fontWeight(isSelected ? .semibold : .regular)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(isSelected ? Color.orange.opacity(0.2) : (isHovered ? Color.surfaceTertiary : Color.clear))
            )
            .foregroundStyle(isSelected ? .orange : (isHovered ? .primary : .secondary))
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Hardware Warning Banner

struct HardwareWarningBanner: View {
    let hardware: HardwareInfo

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)

            VStack(alignment: .leading, spacing: 2) {
                Text("Limited Memory Available")
                    .font(.caption)
                    .fontWeight(.medium)
                Text("Only \(String(format: "%.1f", hardware.availableMemoryGb))GB available. Some models may not run optimally.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text("Recommended: \(hardware.recommendedQuantization)")
                .font(.caption2)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.orange.opacity(0.2))
                .foregroundStyle(.orange)
                .cornerRadius(4)
        }
        .padding(12)
        .background(Color.orange.opacity(0.1))
    }
}

// MARK: - Preview

#Preview {
    HuggingFaceModelsView()
        .frame(width: 1000, height: 700)
}
