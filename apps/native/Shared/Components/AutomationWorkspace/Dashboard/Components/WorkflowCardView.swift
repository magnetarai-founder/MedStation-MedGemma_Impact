//
//  WorkflowCardView.swift
//  MagnetarStudio
//
//  Individual workflow card component for dashboard grid
//

import SwiftUI

// MARK: - Workflow Card

struct WorkflowCardView: View {
    let workflow: WorkflowCard
    let showStarByDefault: Bool
    @State private var isHovered = false
    @State private var isStarred = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Icon chip + Star
            HStack {
                // Icon chip
                HStack(spacing: 6) {
                    Image(systemName: workflow.icon)
                        .font(.system(size: 14))
                        .foregroundStyle(workflow.typeColor)

                    Text(workflow.typeName)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(workflow.typeColor)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(workflow.typeColor.opacity(0.15))
                )

                Spacer()

                // Star toggle
                if showStarByDefault || isHovered {
                    Button {
                        isStarred.toggle()
                    } label: {
                        Image(systemName: isStarred ? "star.fill" : "star")
                            .font(.system(size: 16))
                            .foregroundStyle(isStarred ? .orange : .secondary)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Title
            Text(workflow.name)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Color.textPrimary)

            // Template badge
            if workflow.isTemplate {
                Text("TEMPLATE")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundStyle(.purple)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.purple.opacity(0.15))
                    )
            }

            // Description
            Text(workflow.description)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .lineLimit(2)

            // Visibility badge
            HStack(spacing: 4) {
                Image(systemName: workflow.visibility.icon)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                Text(workflow.visibility.displayName)
                    .font(.caption)
                    .foregroundStyle(.secondary)
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

// MARK: - Agent Assist Card
