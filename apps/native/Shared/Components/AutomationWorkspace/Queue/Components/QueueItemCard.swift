//
//  QueueItemCard.swift
//  MagnetarStudio
//
//  Individual queue item card component
//

import SwiftUI

// MARK: - Queue Item Card

struct QueueItemCard: View {
    let item: QueueItem
    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Priority emoji + Ref pill
            HStack(spacing: 8) {
                Text(item.priority.emoji)
                    .font(.system(size: 20))

                Text(item.reference)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.gray.opacity(0.15))
                    )

                Spacer()
            }

            // Workflow + Stage subtitle
            HStack(spacing: 6) {
                Image(systemName: "arrow.triangle.branch")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)

                Text(item.workflowName)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(Color.textPrimary)

                Text("→")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)

                Text(item.stageName)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }

            // Status pills
            HStack(spacing: 6) {
                ForEach(item.statusLabels, id: \.self) { label in
                    StatusPill(text: label)
                }
            }

            // Data preview section
            if !item.dataPreview.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Data Preview")
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(item.dataPreview.prefix(3), id: \.key) { preview in
                            HStack(spacing: 8) {
                                Text(preview.key)
                                    .font(.system(size: 12))
                                    .foregroundStyle(.secondary)

                                Text(preview.value)
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundStyle(Color.textPrimary)
                            }
                        }
                    }
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.gray.opacity(0.05))
                    )
                }
            }

            // Footer meta
            HStack(spacing: 12) {
                // Created time
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)

                    Text(item.createdAt)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                // Tags
                if !item.tags.isEmpty {
                    HStack(spacing: 4) {
                        Image(systemName: "tag")
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)

                        Text(item.tags.joined(separator: ", "))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                // Assigned info
                if let assignee = item.assignedTo {
                    HStack(spacing: 4) {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text(assignee)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(isHovered ? 0.1 : 0.05), radius: isHovered ? 8 : 4, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(isHovered ? 0.3 : 0.15), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }
}
