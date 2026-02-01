//
//  HuggingFaceModelCard.swift
//  MagnetarStudio (macOS)
//
//  Model card component for HuggingFace GGUF models with VRAM badges and llama.cpp integration
//

import SwiftUI

struct HuggingFaceModelCard: View {
    let model: HuggingFaceModel
    let downloadProgress: DownloadProgress?
    let hardwareInfo: HardwareInfo?
    let onDownload: () -> Void
    let onRun: () -> Void
    let onDelete: () -> Void

    @State private var isHovered: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Icon + Badges + VRAM Indicator
            HStack {
                Image(systemName: "face.smiling.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(huggingFaceGradient)

                Spacer()

                // VRAM compatibility badge
                VRAMBadge(
                    required: model.minVramGb,
                    recommended: model.recommendedVramGb,
                    available: hardwareInfo?.availableMemoryGb
                )

                // Capability badges
                HStack(spacing: 4) {
                    ForEach(model.capabilities.prefix(2), id: \.self) { capability in
                        CapabilityBadge(capability: capability)
                    }
                }
            }

            // Title
            Text(model.name)
                .font(.headline)
                .lineLimit(1)

            // Description
            Text(model.description)
                .font(.caption)
                .foregroundColor(.secondary)
                .lineLimit(2)
                .frame(height: 32, alignment: .top)

            Spacer()

            // Quantization and size info
            HStack(spacing: 12) {
                QuantizationBadge(level: model.quantization)

                HStack(spacing: 4) {
                    Image(systemName: "internaldrive")
                        .font(.caption2)
                    Text(model.sizeFormatted)
                        .font(.caption2)
                }
                .foregroundColor(.secondary)

                Spacer()
            }

            // Action area: Download progress or buttons
            actionArea
        }
        .padding(16)
        .frame(height: 220)
        .background(cardBackground)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.orange.opacity(0.4) : Color.clear, lineWidth: 1)
        )
        .shadow(color: .black.opacity(isHovered ? 0.15 : 0.05), radius: isHovered ? 8 : 4, y: 2)
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isHovered)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    // MARK: - Action Area

    @ViewBuilder
    private var actionArea: some View {
        if let progress = downloadProgress {
            // Download in progress
            VStack(spacing: 4) {
                HStack {
                    Text(progress.message)
                        .font(.caption2)
                        .foregroundColor(progress.error != nil ? .red : .secondary)
                        .lineLimit(1)
                    Spacer()
                    if progress.error == nil {
                        Text("\(Int(progress.progress))%")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                ProgressView(value: progress.progress / 100)
                    .tint(progress.error != nil ? .red : .orange)

                // Speed and ETA for active downloads
                if progress.speedBps > 0 && progress.error == nil {
                    HStack {
                        Text(progress.speedFormatted)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(progress.etaFormatted)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
        } else if model.isDownloaded {
            // Model is downloaded - show Run and Delete buttons
            HStack(spacing: 8) {
                Button {
                    onDelete()
                } label: {
                    Label("Delete", systemImage: "trash")
                        .font(.caption)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.red)
                .controlSize(.small)

                Button {
                    onRun()
                } label: {
                    Label("Run", systemImage: "play.fill")
                        .font(.caption)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.orange)
                .controlSize(.small)
            }
        } else {
            // Not downloaded - show Download button
            Button {
                onDownload()
            } label: {
                Label("Download", systemImage: "arrow.down.circle")
                    .font(.caption)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.orange)
            .controlSize(.small)
        }
    }

    // MARK: - Styling

    private var huggingFaceGradient: LinearGradient {
        LinearGradient(
            colors: [.yellow, .orange],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    private var cardBackground: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(Color.surfaceSecondary.opacity(0.5))
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
            )
    }
}

// MARK: - VRAM Badge

struct VRAMBadge: View {
    let required: Double
    let recommended: Double
    let available: Double?

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: "memorychip")
                .font(.caption2)
            Text(String(format: "%.0fGB", required))
                .font(.caption2)
                .fontWeight(.medium)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .background(badgeColor.opacity(0.2))
        .foregroundColor(badgeColor)
        .cornerRadius(4)
    }

    private var badgeColor: Color {
        guard let available = available else { return .gray }

        if available >= recommended {
            return .green  // Fits comfortably
        } else if available >= required {
            return .yellow  // Tight fit
        } else {
            return .red  // May not fit
        }
    }
}

// MARK: - Quantization Badge

struct QuantizationBadge: View {
    let level: String

    var body: some View {
        Text(level.uppercased())
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(badgeColor.opacity(0.2))
            .foregroundColor(badgeColor)
            .cornerRadius(4)
    }

    private var badgeColor: Color {
        let l = level.lowercased()
        if l.contains("q8") {
            return .purple  // Highest quality
        } else if l.contains("q6") || l.contains("q5") {
            return .blue  // High quality
        } else if l.contains("q4") {
            return .cyan  // Balanced
        } else if l.contains("q3") || l.contains("q2") {
            return .orange  // More compressed
        } else {
            return .gray
        }
    }
}

// MARK: - Capability Badge

struct CapabilityBadge: View {
    let capability: String

    var body: some View {
        Text(capability.uppercased())
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(badgeColor.opacity(0.2))
            .foregroundColor(badgeColor)
            .cornerRadius(4)
    }

    private var badgeColor: Color {
        switch capability.lowercased() {
        case "medical": return .red
        case "code": return .cyan
        case "chat": return .green
        case "vision": return .indigo
        case "reasoning": return .purple
        default: return .gray
        }
    }
}

// MARK: - Preview

#Preview {
    HStack(spacing: 20) {
        // Available model
        HuggingFaceModelCard(
            model: HuggingFaceModel(
                id: "mistral-7b-q4",
                name: "Mistral 7B Instruct",
                repoId: "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                filename: "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                sizeGb: 4.37,
                parameterCount: "7B",
                quantization: "Q4_K_M",
                contextLength: 32768,
                minVramGb: 6.0,
                recommendedVramGb: 8.0,
                capabilities: ["chat", "code"],
                description: "A powerful 7B parameter model fine-tuned for instruction following",
                isDownloaded: false
            ),
            downloadProgress: nil,
            hardwareInfo: HardwareInfo(
                platform: "darwin",
                isAppleSilicon: true,
                totalMemoryGb: 32,
                availableMemoryGb: 24,
                gpuName: "Apple M2 Max",
                gpuVramGb: nil,
                hasMetal: true,
                hasCuda: false,
                recommendedQuantization: "Q4_K_M"
            ),
            onDownload: {},
            onRun: {},
            onDelete: {}
        )

        // Downloaded model
        HuggingFaceModelCard(
            model: HuggingFaceModel(
                id: "codellama-13b-q5",
                name: "CodeLlama 13B",
                repoId: "TheBloke/CodeLlama-13B-GGUF",
                filename: "codellama-13b.Q5_K_M.gguf",
                sizeGb: 9.2,
                parameterCount: "13B",
                quantization: "Q5_K_M",
                contextLength: 16384,
                minVramGb: 10.0,
                recommendedVramGb: 14.0,
                capabilities: ["code"],
                description: "Meta's code-specialized LLM for programming tasks",
                isDownloaded: true
            ),
            downloadProgress: nil,
            hardwareInfo: HardwareInfo(
                platform: "darwin",
                isAppleSilicon: true,
                totalMemoryGb: 32,
                availableMemoryGb: 24,
                gpuName: "Apple M2 Max",
                gpuVramGb: nil,
                hasMetal: true,
                hasCuda: false,
                recommendedQuantization: "Q4_K_M"
            ),
            onDownload: {},
            onRun: {},
            onDelete: {}
        )
    }
    .padding(40)
    .frame(width: 700, height: 300)
    .background(Color.surfacePrimary)
}
