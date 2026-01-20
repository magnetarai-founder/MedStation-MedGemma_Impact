//
//  TeamChatChannelRow.swift
//  MagnetarStudio (macOS)
//
//  Channel row UI component - Extracted from TeamChatComponents.swift (Phase 6.13)
//  Enhanced with hover effects, unread badges, and activity indicators
//

import SwiftUI

struct TeamChatChannelRow: View {
    let channel: TeamChannel
    let isActive: Bool
    let isPrivate: Bool
    var unreadCount: Int = 0
    var lastActivity: String? = nil
    var isMuted: Bool = false

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 8) {
            // Channel icon
            ZStack {
                Circle()
                    .fill(isActive ? Color.magnetarPrimary.opacity(0.2) : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
                    .frame(width: 28, height: 28)

                Image(systemName: channelIcon)
                    .font(.system(size: 12))
                    .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)
            }

            // Channel name
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text(channel.name)
                        .font(.system(size: 14, weight: isActive || unreadCount > 0 ? .semibold : .regular))
                        .foregroundColor(isActive ? .primary : (unreadCount > 0 ? .primary : .secondary))

                    if isMuted {
                        Image(systemName: "speaker.slash.fill")
                            .font(.system(size: 9))
                            .foregroundStyle(.tertiary)
                    }
                }

                // Last activity indicator
                if let activity = lastActivity, !isActive {
                    Text(activity)
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Unread badge
            if unreadCount > 0 {
                Text(unreadCount > 99 ? "99+" : "\(unreadCount)")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(
                        Capsule()
                            .fill(isMuted ? Color.gray : Color.magnetarPrimary)
                    )
            }

            // Hover indicator
            if isHovered && !isActive {
                Image(systemName: "chevron.right")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
                    .transition(.opacity)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : (isHovered ? Color.gray.opacity(0.05) : Color.clear))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(isActive ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }

    private var channelIcon: String {
        if isPrivate {
            return "lock.fill"
        }
        switch channel.type {
        case "direct": return "person.fill"
        case "voice": return "waveform"
        default: return "number"
        }
    }
}
