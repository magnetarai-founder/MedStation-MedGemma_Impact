//
//  WorkspaceSidebarView.swift
//  MedStation
//
//  Simplified sidebar — medical-only.
//

import SwiftUI

struct WorkspaceSidebarView: View {
    @Bindable var store: WorkspaceHubStore

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(alignment: .leading, spacing: 2) {
                Text("MedStation")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.primary)

                Text("Medical AI Assistant")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 16)
            .frame(height: HubLayout.headerHeight)

            Divider()

            Spacer()
        }
        .frame(maxHeight: .infinity)
        .background(Color.surfaceTertiary)
    }
}
