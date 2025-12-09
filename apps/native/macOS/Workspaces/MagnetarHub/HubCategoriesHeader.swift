//
//  HubCategoriesHeader.swift
//  MagnetarStudio (macOS)
//
//  Categories pane header with system badge - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//

import SwiftUI

struct HubCategoriesHeader: View {
    let systemBadgeText: String
    let systemBadgeColor: Color

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: "cube.box.fill")
                    .font(.title2)
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("MagnetarHub")
                    .font(.title3)
                    .fontWeight(.bold)

                Spacer()
            }

            // System Info Badge
            HStack(spacing: 6) {
                Image(systemName: "laptopcomputer")
                    .font(.caption)
                Text(systemBadgeText)
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(systemBadgeColor.opacity(0.2))
            .foregroundColor(systemBadgeColor)
            .cornerRadius(8)
        }
        .padding()
    }
}
