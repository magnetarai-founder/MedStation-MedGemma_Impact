//
//  TemplateGalleryView.swift
//  MagnetarStudio (macOS)
//
//  Full-screen template gallery. Browse, search, preview all templates.
//  Organized by category with "Your Templates" vs "Built-in" sections.
//
//  NOTE: Not yet routed from main navigation. TemplatePickerSheet (used by
//  NotesPanel/SheetsPanel) handles the quick-pick flow. This gallery is intended
//  for a future "Manage Templates" screen accessible from Settings or a dedicated panel.
//

import SwiftUI

struct TemplateGalleryView: View {
    let onSelect: (WorkspaceTemplate) -> Void

    @State private var templateStore = TemplateStore.shared
    @State private var searchText = ""
    @State private var selectedPanel: TemplateTargetPanel?
    @State private var selectedCategory: WorkspaceTemplateCategory?
    @State private var hoveredTemplate: UUID?

    private var filteredTemplates: [WorkspaceTemplate] {
        var templates = templateStore.allTemplates
        if let panel = selectedPanel {
            templates = templates.filter { $0.targetPanel == panel }
        }
        if let category = selectedCategory {
            templates = templates.filter { $0.category == category }
        }
        if !searchText.isEmpty {
            templates = templates.filter {
                $0.name.localizedCaseInsensitiveContains(searchText) ||
                $0.description.localizedCaseInsensitiveContains(searchText)
            }
        }
        return templates
    }

    private var userTemplates: [WorkspaceTemplate] {
        filteredTemplates.filter { !$0.isBuiltin }
    }

    private var builtinTemplates: [WorkspaceTemplate] {
        filteredTemplates.filter { $0.isBuiltin }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar

            Divider()

            // Gallery
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    if !userTemplates.isEmpty {
                        templateSection("Your Templates", templates: userTemplates)
                    }

                    if !builtinTemplates.isEmpty {
                        templateSection("Built-in Templates", templates: builtinTemplates)
                    }

                    if filteredTemplates.isEmpty {
                        emptyState
                    }
                }
                .padding(20)
            }
        }
        .task {
            if templateStore.isLoading {
                await templateStore.loadAll()
            }
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            Image(systemName: "square.grid.2x2")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)

            Text("Templates")
                .font(.system(size: 14, weight: .semibold))

            Spacer()

            // Panel filter
            HStack(spacing: 4) {
                panelFilter(nil, label: "All", icon: "square.grid.2x2")
                ForEach(TemplateTargetPanel.allCases) { panel in
                    panelFilter(panel, label: panel.displayName, icon: panel.icon)
                }
            }

            Divider().frame(height: 16)

            // Search
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                TextField("Search...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .frame(width: 150)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.gray.opacity(0.1))
            )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Template Section

    private func templateSection(_ title: String, templates: [WorkspaceTemplate]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(title)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)
                Text("(\(templates.count))")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
            }

            LazyVGrid(columns: [
                GridItem(.flexible(), spacing: 12),
                GridItem(.flexible(), spacing: 12),
                GridItem(.flexible(), spacing: 12)
            ], spacing: 12) {
                ForEach(templates) { template in
                    galleryCard(template)
                }
            }
        }
    }

    private func galleryCard(_ template: WorkspaceTemplate) -> some View {
        let isHovered = hoveredTemplate == template.id
        return Button { onSelect(template) } label: {
            VStack(alignment: .leading, spacing: 8) {
                // Icon + panel badge
                HStack {
                    ZStack {
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.accentColor.opacity(0.1))
                            .frame(width: 32, height: 32)
                        Image(systemName: template.icon)
                            .font(.system(size: 14))
                            .foregroundStyle(Color.accentColor)
                    }

                    Spacer()

                    Image(systemName: template.targetPanel.icon)
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                }

                // Title + description
                Text(template.name)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(1)

                Text(template.description)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .frame(height: 28, alignment: .top)

                Spacer()

                // Metadata
                HStack(spacing: 6) {
                    Text(template.category.rawValue)
                        .font(.system(size: 9, weight: .medium))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color.gray.opacity(0.1))
                        )

                    if !template.variables.isEmpty {
                        Label("\(template.variables.count)", systemImage: "textformat.abc")
                            .font(.system(size: 9))
                            .foregroundStyle(.tertiary)
                    }
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .frame(height: 140)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.surfaceTertiary)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(isHovered ? Color.accentColor.opacity(0.4) : Color.gray.opacity(0.15), lineWidth: isHovered ? 2 : 1)
            )
            .scaleEffect(isHovered ? 1.02 : 1.0)
            .animation(.easeOut(duration: 0.15), value: isHovered)
        }
        .buttonStyle(.plain)
        .onHover { hoveredTemplate = $0 ? template.id : nil }
    }

    // MARK: - Filters

    private func panelFilter(_ panel: TemplateTargetPanel?, label: String, icon: String) -> some View {
        let isSelected = selectedPanel == panel
        return Button {
            selectedPanel = panel
        } label: {
            Label(label, systemImage: icon)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(isSelected ? .white : .secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isSelected ? Color.accentColor : Color.clear)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "rectangle.on.rectangle.slash")
                .font(.system(size: 36))
                .foregroundStyle(.tertiary)
            Text("No templates found")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
            if !searchText.isEmpty {
                Text("Try a different search term")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }
}
