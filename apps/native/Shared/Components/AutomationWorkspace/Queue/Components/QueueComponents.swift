//
//  QueueComponents.swift
//  MagnetarStudio
//
//  Supporting components for queue view (ToggleButton, StatusPill)
//

import SwiftUI

// MARK: - Supporting Components

struct ToggleButton: View {
    let title: String
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: isActive ? .medium : .regular))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                )
        }
        .buttonStyle(.plain)
    }
}

struct StatusPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(pillColor.opacity(0.2))
            )
            .foregroundColor(pillColor)
    }

    private var pillColor: Color {
        switch text.lowercased() {
        case "pending": return .orange
        case "in progress": return .blue
        case "review": return .purple
        case "blocked": return .red
        case "completed": return .green
        default: return .gray
        }
    }
}
