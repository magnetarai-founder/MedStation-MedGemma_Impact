//
//  MetricCard.swift
//  MagnetarStudio
//
//  Reusable metric card component for analytics
//

import SwiftUI

// MARK: - Metric Card

struct MetricCard: View {
    let title: String
    let value: String
    var subtitle: String? = nil
    let icon: String
    let color: Color
    var isCompact: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: isCompact ? 8 : 12) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: isCompact ? 18 : 24))
                    .foregroundStyle(color)

                Spacer()

                Text(title)
                    .font(.system(size: isCompact ? 12 : 13))
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(value)
                    .font(.system(size: isCompact ? 24 : 32, weight: .bold))
                    .foregroundStyle(Color.textPrimary)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(isCompact ? 12 : 16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(0.15), lineWidth: 1)
        )
    }
}
