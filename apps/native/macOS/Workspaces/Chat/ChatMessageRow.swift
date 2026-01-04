//
//  ChatMessageRow.swift
//  MagnetarStudio (macOS)
//
//  Chat message row component - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatMessageRow: View {
    let message: ChatMessage
    var onRetry: (() -> Void)?  // Optional retry callback for incomplete messages

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
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

            // Incomplete message indicator
            if message.isIncomplete {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)
                        .font(.system(size: 12))

                    Text("Response interrupted")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.orange)

                    Spacer()

                    if let onRetry {
                        Button(action: onRetry) {
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.clockwise")
                                Text("Retry")
                            }
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.white)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(Color.orange)
                            .cornerRadius(4)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, 8)
                .padding(.leading, 44)  // Align with message content
            }
        }
        .padding(12)
        .background(message.role == .user ? Color.magnetarPrimary.opacity(0.06) : Color.surfaceSecondary.opacity(0.4))
        .cornerRadius(10)
    }
}
