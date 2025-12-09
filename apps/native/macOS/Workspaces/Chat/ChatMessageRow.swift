//
//  ChatMessageRow.swift
//  MagnetarStudio (macOS)
//
//  Chat message row component - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatMessageRow: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(message.role == .user ? AnyShapeStyle(LinearGradient.magnetarGradient) : AnyShapeStyle(Color.surfaceSecondary))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: message.role == .user ? "person.fill" : "sparkles")
                        .font(.system(size: 14))
                        .foregroundColor(message.role == .user ? .white : .textSecondary)
                )

            // Message content
            VStack(alignment: .leading, spacing: 4) {
                Text(message.role.displayName)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.textSecondary)

                Text(message.content)
                    .font(.system(size: 14))
                    .textSelection(.enabled)
            }

            Spacer()
        }
        .padding(12)
        .background(message.role == .user ? Color.magnetarPrimary.opacity(0.06) : Color.surfaceSecondary.opacity(0.4))
        .cornerRadius(10)
    }
}
