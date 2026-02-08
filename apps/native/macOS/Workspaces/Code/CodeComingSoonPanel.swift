//
//  CodeComingSoonPanel.swift
//  MagnetarStudio (macOS)
//
//  Placeholder sidebar panel for unimplemented activity bar items (Debug, Extensions).
//

import SwiftUI

struct CodeComingSoonPanel: View {
    let panelName: String
    let icon: String

    var body: some View {
        VStack(spacing: 16) {
            Spacer()

            Image(systemName: icon)
                .font(.system(size: 32))
                .foregroundStyle(.tertiary)

            Text(panelName)
                .font(.headline)
                .foregroundStyle(.secondary)

            Text("Coming Soon")
                .font(.subheadline)
                .foregroundStyle(.tertiary)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
