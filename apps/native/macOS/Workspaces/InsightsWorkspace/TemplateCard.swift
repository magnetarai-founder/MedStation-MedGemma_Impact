//
//  TemplateCard.swift
//  MagnetarStudio
//
//  Template card for template library in Insights Lab
//

import SwiftUI

struct TemplateCard: View {
    let template: InsightsTemplate
    let onApply: () -> Void
    let onEdit: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var categoryColor: Color {
        switch template.category {
        case .general: return .blue
        case .medical: return .red
        case .academic: return .purple
        case .sermon: return .orange
        case .meeting: return .green
        case .legal: return .gray
        case .interview: return .pink
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                // Category badge
                Text(template.category.displayName)
                    .font(.caption2)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(categoryColor.opacity(0.15))
                    .foregroundStyle(categoryColor)
                    .clipShape(RoundedRectangle(cornerRadius: 4))

                Spacer()

                if template.isBuiltin {
                    Image(systemName: "lock.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .help("Built-in template (cannot edit)")
                }
            }

            Text(template.name)
                .font(.headline)
                .lineLimit(1)

            Text(template.description)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(2)

            Spacer()

            HStack(spacing: 8) {
                Button("Apply") {
                    onApply()
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)
                .controlSize(.small)

                Spacer()

                if !template.isBuiltin {
                    Button(action: onEdit) {
                        Image(systemName: "pencil")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                    .help("Edit template")

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.red.opacity(0.7))
                    .help("Delete template")
                }
            }
        }
        .padding()
        .frame(height: 140)
        .background(isHovered ? Color.gray.opacity(0.1) : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.indigo.opacity(0.3) : Color.gray.opacity(0.2), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
