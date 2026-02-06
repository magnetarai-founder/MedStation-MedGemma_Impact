//
//  WorkspaceSidebarView.swift
//  MagnetarStudio
//
//  Sidebar for the Workspace Hub showing panel sections:
//  Notes, Docs, Sheets, PDFs, Voice.
//

import SwiftUI

struct WorkspaceSidebarView: View {
    @Bindable var store: WorkspaceHubStore

    var body: some View {
        VStack(spacing: 0) {
            // Header
            sidebarHeader

            Divider()

            // Panel list (grouped: Content + Manage)
            ScrollView {
                VStack(spacing: 2) {
                    // CONTENT section
                    SidebarSectionHeader(title: "Content")

                    ForEach(WorkspacePanelType.contentPanels) { panel in
                        SidebarPanelRow(
                            panel: panel,
                            isSelected: store.selectedPanel == panel,
                            onSelect: { store.selectPanel(panel) }
                        )
                    }

                    // Team panel (conditional)
                    if teamEnabled {
                        SidebarPanelRow(
                            panel: .team,
                            isSelected: store.selectedPanel == .team,
                            onSelect: { store.selectPanel(.team) }
                        )
                    }

                    // MANAGE section
                    SidebarSectionHeader(title: "Manage")
                        .padding(.top, 8)

                    ForEach(WorkspacePanelType.managementPanels) { panel in
                        SidebarPanelRow(
                            panel: panel,
                            isSelected: store.selectedPanel == panel,
                            onSelect: { store.selectPanel(panel) }
                        )
                    }
                }
                .padding(.horizontal, 8)
                .padding(.top, 8)
            }

            Spacer()

            // Bottom: workspace info
            sidebarFooter
        }
        .frame(maxHeight: .infinity)
        .background(Color.surfaceTertiary)
    }

    // MARK: - Header

    private var sidebarHeader: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Workspace")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.primary)

            Text("Your creation hub")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 16)
        .frame(height: HubLayout.headerHeight)
    }

    // MARK: - Footer

    @AppStorage("workspace.teamEnabled") private var teamEnabled = false

    private var sidebarFooter: some View {
        VStack(spacing: 0) {
            Divider()

            // Team mode toggle
            HStack(spacing: 8) {
                Circle()
                    .fill(teamEnabled ? Color.green : Color.gray.opacity(0.4))
                    .frame(width: 7, height: 7)

                Text(teamEnabled ? "Team Mode" : "Personal")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                Spacer()

                Toggle("", isOn: $teamEnabled)
                    .toggleStyle(.switch)
                    .controlSize(.mini)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
        }
    }
}

// MARK: - Sidebar Panel Row

// MARK: - Sidebar Section Header

private struct SidebarSectionHeader: View {
    let title: String

    var body: some View {
        Text(title.uppercased())
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(.tertiary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 10)
            .padding(.top, 4)
            .padding(.bottom, 2)
    }
}

// MARK: - Sidebar Panel Row

private struct SidebarPanelRow: View {
    let panel: WorkspacePanelType
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: panel.icon)
                    .font(.system(size: 14))
                    .foregroundStyle(isSelected ? Color.magnetarPrimary : .secondary)
                    .frame(width: 20)

                Text(panel.displayName)
                    .font(.system(size: 13, weight: isSelected ? .semibold : .regular))
                    .foregroundStyle(isSelected ? .primary : .secondary)

                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary.opacity(0.12) : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}
