//
//  ModelCard.swift
//  MagnetarStudio (macOS)
//
//  Model card component for MagnetarHub
//

import SwiftUI

struct ModelCard: View {
    let model: AnyModelItem
    let downloadProgress: LegacyDownloadProgress?
    let onDownload: () -> Void
    var enrichedMetadata: [String: EnrichedModelMetadata] = [:] // Add enriched metadata support
    @State private var isHovered: Bool = false
    private let capabilityService = SystemCapabilityService.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Icon + Badge + Compatibility
            HStack {
                Image(systemName: model.icon)
                    .font(.system(size: 32))
                    .foregroundStyle(model.iconGradient)

                Spacer()

                // Compatibility badge
                if let paramSize = model.parameterSize(enriched: enrichedMetadata) {
                    let compatibility = capabilityService.canRunModel(parameterSize: paramSize)
                    Image(systemName: compatibility.performance.icon)
                        .font(.caption2)
                        .foregroundColor(colorForPerformance(compatibility.performance))
                }

                // Multiple badges
                HStack(spacing: 4) {
                    ForEach(model.badges(enriched: enrichedMetadata), id: \.self) { badge in
                        Text(badge.uppercased())
                            .font(.caption2)
                            .fontWeight(.bold)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(model.badgeColor(for: badge).opacity(0.2))
                            .foregroundColor(model.badgeColor(for: badge))
                            .cornerRadius(4)
                    }
                }
            }

            // Title
            Text(model.displayName)
                .font(.headline)
                .lineLimit(1)

            // Description
            if let description = model.description(enriched: enrichedMetadata) {
                Text(description)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
                    .frame(height: 32, alignment: .top)
            }

            Spacer()

            // Download progress or stats
            if let progress = downloadProgress {
                VStack(spacing: 4) {
                    HStack {
                        Text(progress.status)
                            .font(.caption2)
                            .foregroundColor(progress.error != nil ? .red : .secondary)
                        Spacer()
                        if progress.error == nil {
                            Text("\(Int(progress.progress * 100))%")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                    ProgressView(value: progress.progress)
                        .tint(progress.error != nil ? .red : .magnetarPrimary)
                }
            } else if case .backendRecommended = model {
                Button {
                    onDownload()
                } label: {
                    Label("Download", systemImage: "arrow.down.circle")
                        .font(.caption)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            } else {
                // Info for local/cloud models - now shows as button hint
                VStack(spacing: 8) {
                    VStack(spacing: 6) {
                        if let stat1 = model.stat1 {
                            HStack(spacing: 6) {
                                Image(systemName: stat1.icon)
                                    .font(.caption2)
                                Text(stat1.text)
                                    .font(.caption2)
                                Spacer()
                            }
                            .foregroundColor(.secondary)
                        }

                        if let stat2 = model.stat2 {
                            HStack(spacing: 6) {
                                Image(systemName: stat2.icon)
                                    .font(.caption2)
                                Text(stat2.text)
                                    .font(.caption2)
                                Spacer()
                            }
                            .foregroundColor(.secondary)
                        }
                    }

                    // Visual hint that card is clickable
                    HStack {
                        Spacer()
                        Text("View Details")
                            .font(.caption2)
                            .foregroundColor(.magnetarPrimary.opacity(0.7))
                        Image(systemName: "chevron.right")
                            .font(.caption2)
                            .foregroundColor(.magnetarPrimary.opacity(0.7))
                    }
                }
            }
        }
        .padding(16)
        .frame(height: 200)
        .background(cardBackground)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .shadow(color: .black.opacity(isHovered ? 0.15 : 0.05), radius: isHovered ? 8 : 4, y: 2)
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isHovered)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    private var cardBackground: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(Color.surfaceSecondary.opacity(0.5))
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.ultraThinMaterial)
            )
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
}
