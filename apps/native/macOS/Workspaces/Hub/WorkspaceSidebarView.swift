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
    @State private var showTemplateGallery = false
    @State private var editingTemplate: WorkspaceTemplate?

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

                    // Team panel — gated by FeatureFlags (coming in future upgrade)
                    if FeatureFlags.shared.team {
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

            // Bottom: Manage Templates + workspace info
            Button {
                showTemplateGallery = true
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "doc.on.doc")
                        .font(.system(size: 11))
                    Text("Manage Templates")
                        .font(.system(size: 11))
                }
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 14)
                .padding(.vertical, 6)
            }
            .buttonStyle(.plain)

            sidebarFooter
        }
        .frame(maxHeight: .infinity)
        .background(Color.surfaceTertiary)
        .sheet(isPresented: $showTemplateGallery) {
            TemplateGalleryView(onSelect: { template in
                editingTemplate = template
                showTemplateGallery = false
            })
            .frame(minWidth: 600, minHeight: 450)
        }
        .sheet(item: $editingTemplate) { template in
            TemplateEditorView(
                template: template,
                onSave: { updated in
                    TemplateStore.shared.save(template: updated)
                    editingTemplate = nil
                },
                onCancel: { editingTemplate = nil }
            )
        }
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

    private var sidebarFooter: some View {
        VStack(spacing: 0) {
            Divider()

            HStack(spacing: 8) {
                Circle()
                    .fill(Color.gray.opacity(0.4))
                    .frame(width: 7, height: 7)

                Text("Personal")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                Spacer()

                Text("Team Coming Soon")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.1))
                    )
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
