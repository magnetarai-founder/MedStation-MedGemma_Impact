//
//  TeamChatSectionHeader.swift
//  MagnetarStudio (macOS)
//
//  Sidebar section header with optional add button - Extracted from TeamChatComponents.swift (Phase 6.13)
//

import SwiftUI

struct TeamChatSectionHeader: View {
    let title: String
    let onAdd: (() -> Void)?

    var body: some View {
        HStack {
            Text(title)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.secondary)
                .textCase(.uppercase)

            Spacer()

            if let onAdd = onAdd {
                Button(action: onAdd) {
                    Image(systemName: "plus")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 20, height: 20)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
    }
}
