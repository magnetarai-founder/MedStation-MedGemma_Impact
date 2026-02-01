//
//  HardwareValidationView.swift
//  MagnetarStudio (macOS)
//
//  Hardware validation modal showing system info and model compatibility
//

import SwiftUI

struct HardwareValidationView: View {
    let model: HuggingFaceModel
    let hardware: HardwareInfo
    let validation: ModelValidation?
    let onDismiss: () -> Void
    let onProceed: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    systemInfoSection
                    modelRequirementsSection
                    compatibilitySection
                }
                .padding(24)
            }

            Divider()

            // Actions
            actions
        }
        .frame(width: 480, height: 500)
        .background(Color.surfacePrimary)
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Hardware Validation")
                    .font(.headline)
                Text("Check if your system can run this model")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Button {
                onDismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(16)
    }

    // MARK: - System Info

    private var systemInfoSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Your System", icon: "desktopcomputer")

            VStack(spacing: 8) {
                InfoRow(
                    label: "Platform",
                    value: hardware.isAppleSilicon ? "Apple Silicon" : hardware.platform.capitalized,
                    icon: "cpu"
                )

                InfoRow(
                    label: "Total Memory",
                    value: String(format: "%.0f GB", hardware.totalMemoryGb),
                    icon: "memorychip"
                )

                InfoRow(
                    label: "Available Memory",
                    value: String(format: "%.1f GB", hardware.availableMemoryGb),
                    icon: "memorychip.fill",
                    valueColor: hardware.availableMemoryGb >= model.minVramGb ? .green : .orange
                )

                if let gpu = hardware.gpuName {
                    InfoRow(
                        label: "GPU",
                        value: gpu,
                        icon: "display"
                    )
                }

                HStack(spacing: 16) {
                    if hardware.hasMetal {
                        AcceleratorBadge(name: "Metal", isAvailable: true)
                    }
                    if hardware.hasCuda {
                        AcceleratorBadge(name: "CUDA", isAvailable: true)
                    }
                }
                .padding(.top, 4)
            }
            .padding(12)
            .background(Color.surfaceSecondary.opacity(0.5))
            .cornerRadius(8)
        }
    }

    // MARK: - Model Requirements

    private var modelRequirementsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Model Requirements", icon: "cube.box")

            VStack(spacing: 8) {
                InfoRow(
                    label: "Model",
                    value: model.name,
                    icon: "face.smiling"
                )

                InfoRow(
                    label: "Size",
                    value: model.sizeFormatted,
                    icon: "internaldrive"
                )

                InfoRow(
                    label: "Minimum VRAM",
                    value: String(format: "%.1f GB", model.minVramGb),
                    icon: "memorychip",
                    valueColor: hardware.availableMemoryGb >= model.minVramGb ? .primary : .red
                )

                InfoRow(
                    label: "Recommended VRAM",
                    value: String(format: "%.1f GB", model.recommendedVramGb),
                    icon: "memorychip.fill",
                    valueColor: hardware.availableMemoryGb >= model.recommendedVramGb ? .green : .orange
                )

                InfoRow(
                    label: "Quantization",
                    value: model.quantization,
                    icon: "square.stack.3d.up"
                )

                InfoRow(
                    label: "Context Length",
                    value: "\(model.contextLength) tokens",
                    icon: "text.alignleft"
                )
            }
            .padding(12)
            .background(Color.surfaceSecondary.opacity(0.5))
            .cornerRadius(8)
        }
    }

    // MARK: - Compatibility

    private var compatibilitySection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "Compatibility", icon: "checkmark.shield")

            compatibilityCard
        }
    }

    @ViewBuilder
    private var compatibilityCard: some View {
        let status = computeCompatibility()

        HStack(spacing: 16) {
            Image(systemName: status.icon)
                .font(.system(size: 36))
                .foregroundColor(status.color)

            VStack(alignment: .leading, spacing: 4) {
                Text(status.title)
                    .font(.headline)
                    .foregroundColor(status.color)
                Text(status.message)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(16)
        .background(status.color.opacity(0.1))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(status.color.opacity(0.3), lineWidth: 1)
        )
    }

    private func computeCompatibility() -> (icon: String, title: String, message: String, color: Color) {
        if let validation = validation {
            if validation.compatible {
                return (
                    "checkmark.circle.fill",
                    "Compatible",
                    validation.message,
                    .green
                )
            } else {
                return (
                    "xmark.circle.fill",
                    "Not Compatible",
                    validation.message,
                    .red
                )
            }
        }

        // Fallback to local calculation
        if hardware.availableMemoryGb >= model.recommendedVramGb {
            return (
                "checkmark.circle.fill",
                "Excellent Fit",
                "Your system exceeds the recommended requirements.",
                .green
            )
        } else if hardware.availableMemoryGb >= model.minVramGb {
            return (
                "exclamationmark.triangle.fill",
                "Tight Fit",
                "Your system meets minimum requirements. Performance may vary.",
                .orange
            )
        } else {
            return (
                "xmark.circle.fill",
                "May Not Run",
                "Your system doesn't meet the minimum VRAM requirement.",
                .red
            )
        }
    }

    // MARK: - Actions

    private var actions: some View {
        HStack(spacing: 12) {
            Button("Cancel") {
                onDismiss()
            }
            .buttonStyle(.bordered)

            Spacer()

            let canProceed = hardware.availableMemoryGb >= model.minVramGb

            Button {
                onProceed()
            } label: {
                Label(
                    canProceed ? "Download Model" : "Download Anyway",
                    systemImage: "arrow.down.circle"
                )
            }
            .buttonStyle(.borderedProminent)
            .tint(canProceed ? .orange : .red)
        }
        .padding(16)
    }
}

// MARK: - Supporting Views

struct SectionHeader: View {
    let title: String
    let icon: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .foregroundColor(.magnetarPrimary)
            Text(title)
                .font(.subheadline)
                .fontWeight(.semibold)
        }
    }
}

struct InfoRow: View {
    let label: String
    let value: String
    let icon: String
    var valueColor: Color = .primary

    var body: some View {
        HStack {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .frame(width: 16)
                Text(label)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Text(value)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(valueColor)
        }
    }
}

struct AcceleratorBadge: View {
    let name: String
    let isAvailable: Bool

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: isAvailable ? "checkmark.circle.fill" : "xmark.circle")
                .font(.caption2)
            Text(name)
                .font(.caption2)
                .fontWeight(.medium)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(isAvailable ? Color.green.opacity(0.2) : Color.gray.opacity(0.2))
        .foregroundColor(isAvailable ? .green : .gray)
        .cornerRadius(4)
    }
}

// MARK: - Preview

#Preview {
    HardwareValidationView(
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
        hardware: HardwareInfo(
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
        validation: ModelValidation(
            modelId: "mistral-7b-q4",
            compatible: true,
            message: "Your system can run this model with excellent performance.",
            modelSizeGb: 4.37,
            minVramGb: 6.0,
            availableVramGb: 24.0
        ),
        onDismiss: {},
        onProceed: {}
    )
}
