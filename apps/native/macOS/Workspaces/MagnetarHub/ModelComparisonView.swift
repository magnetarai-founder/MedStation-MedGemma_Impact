//
//  ModelComparisonView.swift
//  MagnetarStudio (macOS)
//
//  Side-by-side comparison of Ollama vs HuggingFace models
//

import SwiftUI

struct ModelComparisonView: View {
    @State private var leftModel: ComparisonModel?
    @State private var rightModel: ComparisonModel?
    @State private var availableOllamaModels: [OllamaModel] = []
    @State private var availableHuggingFaceModels: [HuggingFaceModel] = []
    @State private var isLoading = false

    let onDismiss: () -> Void

    private let modelsStore = ModelsStore.shared
    private let huggingFaceService = HuggingFaceService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Comparison content
            HStack(spacing: 0) {
                // Left column
                ModelComparisonColumn(
                    model: $leftModel,
                    availableOllama: availableOllamaModels,
                    availableHuggingFace: availableHuggingFaceModels,
                    side: .left
                )

                // Swap button and divider
                VStack {
                    Spacer()
                    Button {
                        swap(&leftModel, &rightModel)
                    } label: {
                        Image(systemName: "arrow.left.arrow.right")
                            .font(.title2)
                            .foregroundStyle(Color.magnetarPrimary)
                            .frame(width: 44, height: 44)
                            .background(Circle().fill(Color.surfaceTertiary))
                    }
                    .buttonStyle(.plain)
                    .help("Swap models")
                    Spacer()
                }
                .frame(width: 60)

                // Right column
                ModelComparisonColumn(
                    model: $rightModel,
                    availableOllama: availableOllamaModels,
                    availableHuggingFace: availableHuggingFaceModels,
                    side: .right
                )
            }

            // Comparison summary (if both selected)
            if leftModel != nil && rightModel != nil {
                Divider()
                comparisonSummary
            }
        }
        .frame(width: 800, height: 600)
        .background(Color.surfacePrimary)
        .task {
            await loadModels()
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Model Comparison")
                    .font(.headline)
                Text("Compare specifications across model sources")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Button {
                onDismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.title2)
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(16)
    }

    // MARK: - Comparison Summary

    private var comparisonSummary: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Comparison")
                .font(.subheadline)
                .fontWeight(.semibold)

            HStack(spacing: 24) {
                // Size comparison
                ComparisonMetric(
                    label: "Size",
                    leftValue: leftModel?.sizeFormatted ?? "-",
                    rightValue: rightModel?.sizeFormatted ?? "-",
                    leftBetter: compareSize(left: leftModel, right: rightModel)
                )

                Divider()
                    .frame(height: 40)

                // VRAM comparison
                ComparisonMetric(
                    label: "Min VRAM",
                    leftValue: leftModel?.minVramFormatted ?? "-",
                    rightValue: rightModel?.minVramFormatted ?? "-",
                    leftBetter: compareVram(left: leftModel, right: rightModel)
                )

                Divider()
                    .frame(height: 40)

                // Context length
                ComparisonMetric(
                    label: "Context",
                    leftValue: leftModel?.contextFormatted ?? "-",
                    rightValue: rightModel?.contextFormatted ?? "-",
                    leftBetter: compareContext(left: leftModel, right: rightModel)
                )

                Divider()
                    .frame(height: 40)

                // Quantization
                ComparisonMetric(
                    label: "Quantization",
                    leftValue: leftModel?.quantization ?? "-",
                    rightValue: rightModel?.quantization ?? "-",
                    leftBetter: nil  // No clear "better" for quantization
                )
            }
        }
        .padding(16)
        .background(Color.surfaceSecondary.opacity(0.5))
    }

    // MARK: - Data Loading

    private func loadModels() async {
        isLoading = true

        // Load Ollama models
        availableOllamaModels = modelsStore.models

        // Load HuggingFace models
        do {
            availableHuggingFaceModels = try await huggingFaceService.listAvailableModels()
        } catch {
            // Silently fail - user can still compare Ollama models
        }

        isLoading = false
    }

    // MARK: - Comparison Helpers

    private func compareSize(left: ComparisonModel?, right: ComparisonModel?) -> Bool? {
        guard let l = left?.sizeGb, let r = right?.sizeGb else { return nil }
        return l < r  // Smaller is better
    }

    private func compareVram(left: ComparisonModel?, right: ComparisonModel?) -> Bool? {
        guard let l = left?.minVramGb, let r = right?.minVramGb else { return nil }
        return l < r  // Lower VRAM requirement is better
    }

    private func compareContext(left: ComparisonModel?, right: ComparisonModel?) -> Bool? {
        guard let l = left?.contextLength, let r = right?.contextLength else { return nil }
        return l > r  // Larger context is better
    }
}

// MARK: - Comparison Model (unified wrapper)

enum ModelSource: String, CaseIterable {
    case ollama = "Ollama"
    case huggingface = "HuggingFace"

    var icon: String {
        switch self {
        case .ollama: return "cube.box.fill"
        case .huggingface: return "face.smiling.fill"
        }
    }

    var color: Color {
        switch self {
        case .ollama: return .magnetarPrimary
        case .huggingface: return .orange
        }
    }
}

struct ComparisonModel: Identifiable {
    let id: String
    let name: String
    let source: ModelSource
    let sizeGb: Double?
    let minVramGb: Double?
    let contextLength: Int?
    let quantization: String?
    let capabilities: [String]
    let description: String?

    var sizeFormatted: String {
        guard let size = sizeGb else { return "-" }
        return String(format: "%.1f GB", size)
    }

    var minVramFormatted: String {
        guard let vram = minVramGb else { return "-" }
        return String(format: "%.1f GB", vram)
    }

    var contextFormatted: String {
        guard let ctx = contextLength else { return "-" }
        if ctx >= 1000 {
            return "\(ctx / 1000)K"
        }
        return "\(ctx)"
    }

    static func from(ollama: OllamaModel) -> ComparisonModel {
        ComparisonModel(
            id: "ollama-\(ollama.id)",
            name: ollama.name,
            source: .ollama,
            sizeGb: ollama.size > 0 ? Double(ollama.size) / (1024 * 1024 * 1024) : nil,
            minVramGb: nil,  // Ollama doesn't expose VRAM requirements directly
            contextLength: nil,
            quantization: nil,
            capabilities: [],
            description: nil
        )
    }

    static func from(huggingface: HuggingFaceModel) -> ComparisonModel {
        ComparisonModel(
            id: "hf-\(huggingface.id)",
            name: huggingface.name,
            source: .huggingface,
            sizeGb: huggingface.sizeGb,
            minVramGb: huggingface.minVramGb,
            contextLength: huggingface.contextLength,
            quantization: huggingface.quantization,
            capabilities: huggingface.capabilities,
            description: huggingface.description
        )
    }
}

// MARK: - Comparison Column

enum ComparisonSide {
    case left, right
}

struct ModelComparisonColumn: View {
    @Binding var model: ComparisonModel?
    let availableOllama: [OllamaModel]
    let availableHuggingFace: [HuggingFaceModel]
    let side: ComparisonSide

    @State private var selectedSource: ModelSource = .ollama
    @State private var isHovered = false

    var body: some View {
        VStack(spacing: 0) {
            // Source selector
            Picker("Source", selection: $selectedSource) {
                ForEach(ModelSource.allCases, id: \.self) { source in
                    Label(source.rawValue, systemImage: source.icon)
                        .tag(source)
                }
            }
            .pickerStyle(.segmented)
            .padding()

            Divider()

            // Model selector
            ScrollView {
                LazyVStack(spacing: 8) {
                    if selectedSource == .ollama {
                        ForEach(availableOllama) { ollamaModel in
                            ModelSelectionRow(
                                name: ollamaModel.name,
                                subtitle: ollamaModel.sizeFormatted,
                                icon: "cube.box.fill",
                                color: .magnetarPrimary,
                                isSelected: model?.id == "ollama-\(ollamaModel.id)",
                                action: {
                                    model = ComparisonModel.from(ollama: ollamaModel)
                                }
                            )
                        }
                    } else {
                        ForEach(availableHuggingFace) { hfModel in
                            ModelSelectionRow(
                                name: hfModel.name,
                                subtitle: "\(hfModel.sizeFormatted) • \(hfModel.quantization)",
                                icon: "face.smiling.fill",
                                color: .orange,
                                isSelected: model?.id == "hf-\(hfModel.id)",
                                action: {
                                    model = ComparisonModel.from(huggingface: hfModel)
                                }
                            )
                        }
                    }
                }
                .padding()
            }

            // Selected model details
            if let selected = model {
                Divider()
                selectedModelDetails(selected)
            }
        }
        .frame(maxWidth: .infinity)
        .background(isHovered ? Color.surfaceSecondary.opacity(0.3) : Color.clear)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    @ViewBuilder
    private func selectedModelDetails(_ model: ComparisonModel) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: model.source.icon)
                    .foregroundStyle(model.source.color)
                Text(model.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }

            VStack(alignment: .leading, spacing: 4) {
                if let desc = model.description {
                    Text(desc)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                HStack(spacing: 8) {
                    if !model.capabilities.isEmpty {
                        ForEach(model.capabilities.prefix(3), id: \.self) { cap in
                            Text(cap.uppercased())
                                .font(.caption2)
                                .fontWeight(.bold)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.magnetarPrimary.opacity(0.2))
                                .foregroundStyle(Color.magnetarPrimary)
                                .cornerRadius(4)
                        }
                    }
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.surfaceTertiary.opacity(0.5))
    }
}

// MARK: - Model Selection Row

struct ModelSelectionRow: View {
    let name: String
    let subtitle: String
    let icon: String
    let color: Color
    let isSelected: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .foregroundStyle(color)

                VStack(alignment: .leading, spacing: 2) {
                    Text(name)
                        .font(.caption)
                        .fontWeight(isSelected ? .semibold : .regular)
                        .lineLimit(1)
                    Text(subtitle)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(color)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? color.opacity(0.15) : (isHovered ? Color.surfaceTertiary : Color.clear))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? color.opacity(0.3) : Color.clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Comparison Metric

struct ComparisonMetric: View {
    let label: String
    let leftValue: String
    let rightValue: String
    let leftBetter: Bool?  // nil = neither is better

    var body: some View {
        VStack(spacing: 8) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)

            HStack(spacing: 16) {
                Text(leftValue)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(indicatorColor(isLeft: true))

                Text("vs")
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                Text(rightValue)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundStyle(indicatorColor(isLeft: false))
            }
        }
    }

    private func indicatorColor(isLeft: Bool) -> Color {
        guard let better = leftBetter else { return .primary }
        if isLeft && better { return .green }
        if !isLeft && !better { return .green }
        return .primary
    }
}

// MARK: - Preview

#Preview {
    ModelComparisonView(onDismiss: {})
}
