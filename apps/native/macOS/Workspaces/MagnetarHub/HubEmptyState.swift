//
//  HubEmptyState.swift
//  MagnetarStudio (macOS)
//
//  Empty state view for MagnetarHub - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//

import SwiftUI

struct HubEmptyState: View {
    let category: HubCategory

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: category.emptyIcon)
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text(category.emptyTitle)
                .font(.title3)
                .fontWeight(.semibold)

            Text(category.emptySubtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}
