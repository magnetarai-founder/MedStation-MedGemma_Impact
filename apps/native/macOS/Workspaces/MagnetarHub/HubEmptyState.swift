//
//  HubEmptyState.swift
//  MagnetarStudio (macOS)
//
//  Empty state view for MagnetarHub - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//  Enhanced with gradient icon and action hints
//

import SwiftUI

struct HubEmptyState: View {
    let category: HubCategory

    var body: some View {
        VStack(spacing: 16) {
            // Icon with gradient background
            ZStack {
                Circle()
                    .fill(iconGradient.opacity(0.15))
                    .frame(width: 80, height: 80)

                Image(systemName: category.emptyIcon)
                    .font(.system(size: 36))
                    .foregroundStyle(iconGradient)
            }

            VStack(spacing: 6) {
                Text(category.emptyTitle)
                    .font(.title3)
                    .fontWeight(.semibold)

                Text(category.emptySubtitle)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            // Action hint based on category
            if let actionHint = actionHint {
                HStack(spacing: 6) {
                    Image(systemName: actionHint.icon)
                        .font(.system(size: 12))
                    Text(actionHint.text)
                        .font(.caption)
                }
                .foregroundStyle(iconGradient)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(iconGradient.opacity(0.1))
                .clipShape(Capsule())
                .padding(.top, 8)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }

    private var iconGradient: LinearGradient {
        switch category {
        case .myModels:
            return LinearGradient.magnetarGradient
        case .discover:
            return LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
        case .cloud:
            return LinearGradient(colors: [.purple, .pink], startPoint: .topLeading, endPoint: .bottomTrailing)
        }
    }

    private var actionHint: (icon: String, text: String)? {
        switch category {
        case .myModels:
            return ("arrow.right.circle", "Browse Discover tab to download models")
        case .discover:
            return ("globe", "Check your network connection")
        case .cloud:
            return ("person.badge.key", "Sign in to sync your models")
        }
    }
}
