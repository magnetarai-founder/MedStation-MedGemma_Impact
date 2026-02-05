//
//  TemplatePickerSheet.swift
//  MagnetarStudio (macOS)
//
//  Compact template picker shown when creating a new note/doc/sheet.
//  Shows "Blank" option + grid of available templates for the target panel.
//

import SwiftUI

struct TemplatePickerSheet: View {
    let targetPanel: TemplateTargetPanel
    let onBlank: () -> Void
    let onTemplate: (WorkspaceTemplate) -> Void
    let onDismiss: () -> Void

    @State private var templateStore = TemplateStore.shared
    @State private var searchText = ""
    @State private var selectedCategory: WorkspaceTemplateCategory?

    private var filteredTemplates: [WorkspaceTemplate] {
        var templates = templateStore.templates(for: targetPanel)
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

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("New \(targetPanel.displayName)")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
                Button { onDismiss() } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            // Search + Category filter
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                TextField("Search templates...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            // Category chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    categoryChip(nil, label: "All")
                    ForEach(WorkspaceTemplateCategory.allCases) { category in
                        categoryChip(category, label: category.rawValue)
                    }
                }
                .padding(.horizontal, 16)
            }
            .padding(.bottom, 8)

            Divider()

            // Template grid
            ScrollView {
                LazyVGrid(columns: [
                    GridItem(.flexible(), spacing: 12),
                    GridItem(.flexible(), spacing: 12)
                ], spacing: 12) {
                    // Blank option always first
                    blankCard

                    // Templates
                    ForEach(filteredTemplates) { template in
                        templateCard(template)
                    }
                }
                .padding(16)
            }
        }
        .frame(width: 480, height: 420)
        .task {
            if templateStore.isLoading {
                await templateStore.loadAll()
            }
        }
    }

    // MARK: - Components

    private var blankCard: some View {
        Button { onBlank() } label: {
            VStack(spacing: 8) {
                Image(systemName: "plus")
                    .font(.system(size: 24))
                    .foregroundStyle(.secondary)
                Text("Blank")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.primary)
                Text("Start from scratch")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 100)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.gray.opacity(0.3), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
            )
        }
        .buttonStyle(.plain)
    }

    private func templateCard(_ template: WorkspaceTemplate) -> some View {
        Button { onTemplate(template) } label: {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    Image(systemName: template.icon)
                        .font(.system(size: 14))
                        .foregroundStyle(Color.accentColor)
                    Text(template.name)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                }

                Text(template.description)
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                Spacer()

                HStack {
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
                        Text("\(template.variables.count) fields")
                            .font(.system(size: 9))
                            .foregroundStyle(.tertiary)
                    }
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .frame(height: 100)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.surfaceTertiary)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.gray.opacity(0.15), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private func categoryChip(_ category: WorkspaceTemplateCategory?, label: String) -> some View {
        let isSelected = selectedCategory == category
        return Button {
            selectedCategory = category
        } label: {
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(isSelected ? .white : .secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(isSelected ? Color.accentColor : Color.gray.opacity(0.1))
                )
        }
        .buttonStyle(.plain)
    }
}
