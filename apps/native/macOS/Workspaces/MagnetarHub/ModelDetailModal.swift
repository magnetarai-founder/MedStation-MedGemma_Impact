//
//  ModelDetailModal.swift
//  MagnetarStudio (macOS)
//
//  Model detail modal view for MagnetarHub
//

import SwiftUI

struct ModelDetailModal: View {
    let model: AnyModelItem
    let enrichedMetadata: [String: EnrichedModelMetadata]
    @Binding var activeDownloads: [String: DownloadProgress]
    let onDownload: (String) -> Void
    let onDelete: (String) -> Void
    let onUpdate: (String) -> Void
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

                    // Multiple badges in detail modal
                    HStack(spacing: 6) {
                        ForEach(model.badges(enriched: enrichedMetadata), id: \.self) { badge in
                            Text(badge.uppercased())
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(model.badgeColor(for: badge).opacity(0.2))
                                .foregroundColor(model.badgeColor(for: badge))
                                .cornerRadius(6)
                        }
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
                    if case .backendRecommended(let backendModel) = model {
                        compatibilitySection(for: backendModel)
                    }

                    // Description
                    if let description = model.description(enriched: enrichedMetadata) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Description")
                                .font(.headline)
                            Text(description)
                                .foregroundColor(.secondary)
                        }
                    }

                    // Actions
                    model.detailActions(
                        activeDownloads: $activeDownloads,
                        onDownload: onDownload,
                        onDelete: onDelete,
                        onUpdate: onUpdate
                    )

                    // Additional details
                    model.additionalDetails(enriched: enrichedMetadata)
                }
                .padding(24)
            }
        }
        .frame(width: 600, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    @ViewBuilder
    private func compatibilitySection(for backendModel: BackendRecommendedModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("System Compatibility")
                .font(.headline)

            // System info
            Text(capabilityService.getSystemSummary())
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.vertical, 4)

            // Use backend-provided compatibility info
            let performance = backendModel.compatibility.performance
            let icon = performanceIcon(for: performance)
            let color = colorForPerformanceString(performance)

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 12) {
                    Image(systemName: icon)
                        .foregroundColor(color)
                        .frame(width: 20)

                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) {
                            Text(friendlyModelSizeName(backendModel.parameterSize))
                                .font(.body)
                                .fontWeight(.medium)

                            Text("(\(backendModel.parameterSize))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        Text(backendModel.compatibility.reason)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    if let memUsage = backendModel.compatibility.estimatedMemoryUsage {
                        Text(String(format: "~%.1fGB", memUsage))
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
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

    private func colorForPerformanceString(_ performance: String) -> Color {
        switch performance.lowercased() {
        case "excellent": return .green
        case "good": return .blue
        case "fair": return .orange
        case "insufficient": return .red
        default: return .secondary
        }
    }

    private func performanceIcon(for performance: String) -> String {
        switch performance.lowercased() {
        case "excellent": return "checkmark.circle.fill"
        case "good": return "checkmark.circle"
        case "fair": return "exclamationmark.triangle"
        case "insufficient": return "xmark.circle"
        default: return "questionmark.circle"
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
