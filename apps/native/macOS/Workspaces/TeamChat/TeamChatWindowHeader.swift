//
//  TeamChatWindowHeader.swift
//  MagnetarStudio (macOS)
//
//  Chat window header component - Extracted from TeamChatComponents.swift (Phase 6.13)
//

import SwiftUI

struct TeamChatWindowHeader: View {
    let channel: TeamChannel

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "number")
                .font(.system(size: 18))
                .foregroundStyle(Color.magnetarPrimary)

            Text(channel.name)
                .font(.system(size: 18, weight: .bold))

            Spacer()

            Button {
                // Channel menu
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 16))
                    .foregroundStyle(.secondary)
                    .frame(width: 32, height: 32)
            }
            .buttonStyle(.plain)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.0))
            )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(.controlBackgroundColor))
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.2))
                .frame(height: 1),
            alignment: .bottom
        )
    }
}
