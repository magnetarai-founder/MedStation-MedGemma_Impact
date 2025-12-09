//
//  TeamChatChannelRow.swift
//  MagnetarStudio (macOS)
//
//  Channel row UI component - Extracted from TeamChatComponents.swift (Phase 6.13)
//

import SwiftUI

struct TeamChatChannelRow: View {
    let channel: TeamChannel
    let isActive: Bool
    let isPrivate: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: isPrivate ? "lock" : "number")
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            Text(channel.name)
                .font(.system(size: 14))
                .foregroundColor(isActive ? .primary : .secondary)

            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .strokeBorder(isActive ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
                )
        )
    }
}
