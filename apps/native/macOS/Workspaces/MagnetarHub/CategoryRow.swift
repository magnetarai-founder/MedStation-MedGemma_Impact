//
//  CategoryRow.swift
//  MagnetarStudio (macOS)
//
//  Category row component for MagnetarHub sidebar
//

import SwiftUI

struct CategoryRow: View {
    let category: HubCategory

    var body: some View {
        Label {
            VStack(alignment: .leading, spacing: 2) {
                Text(category.displayName)
                    .font(.headline)
                Text(category.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        } icon: {
            Image(systemName: category.icon)
                .foregroundStyle(LinearGradient.magnetarGradient)
        }
        .padding(.vertical, 4)
    }
}
