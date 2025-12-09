//
//  ChatSessionRow.swift
//  MagnetarStudio (macOS)
//
//  Chat session row component - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatSessionRow: View {
    let session: ChatSession
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(session.title)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .foregroundColor(.textPrimary)

                // Sessions don't have fixed models - show "Multi-model" or "Intelligent"
                Text("Multi-model")
                    .font(.system(size: 11))
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(LinearGradient.magnetarGradient)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.12) : Color.clear)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .strokeBorder(isSelected ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
    }
}
