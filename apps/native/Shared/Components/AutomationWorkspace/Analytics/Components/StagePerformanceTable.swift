//
//  StagePerformanceTable.swift
//  MagnetarStudio
//
//  Table showing performance metrics for workflow stages
//

import SwiftUI

// MARK: - Stage Performance Table

struct StagePerformanceTable: View {
    let stages: [LegacyStagePerformance]

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 16) {
                Text("Stage")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Entered")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 80, alignment: .trailing)

                Text("Completed")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Avg Time")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Median Time")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 100, alignment: .trailing)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.05))

            Divider()

            // Rows
            ForEach(stages) { stage in
                VStack(spacing: 0) {
                    HStack(spacing: 16) {
                        Text(stage.name)
                            .font(.system(size: 14))
                            .foregroundStyle(Color.textPrimary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        Text("\(stage.entered)")
                            .font(.system(size: 14))
                            .foregroundStyle(Color.textPrimary)
                            .frame(width: 80, alignment: .trailing)

                        Text("\(stage.completed)")
                            .font(.system(size: 14))
                            .foregroundStyle(Color.textPrimary)
                            .frame(width: 100, alignment: .trailing)

                        Text(stage.avgTime)
                            .font(.system(size: 14, design: .monospaced))
                            .foregroundStyle(Color.textPrimary)
                            .frame(width: 100, alignment: .trailing)

                        Text(stage.medianTime ?? "—")
                            .font(.system(size: 14, design: .monospaced))
                            .foregroundStyle(stage.medianTime != nil ? Color.textPrimary : .secondary)
                            .frame(width: 100, alignment: .trailing)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)

                    if stage.id != stages.last?.id {
                        Divider()
                    }
                }
                .background(Color.clear)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.15), lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }
}
