//
//  TemplateLibrarySheet.swift
//  MagnetarStudio
//
//  Template library sheet for Insights Lab
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TemplateLibrarySheet")

struct TemplateLibrarySheet: View {
    let templates: [InsightsTemplate]
    let onApply: (String) async -> Void
    let onRefresh: () async -> Void
    let onEditTemplate: (InsightsTemplate?) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedCategory: TemplateCategory?
    @State private var searchText = ""

    var filteredTemplates: [InsightsTemplate] {
        var result = templates
        if let category = selectedCategory {
            result = result.filter { $0.category == category }
        }
        if !searchText.isEmpty {
            result = result.filter {
                $0.name.localizedCaseInsensitiveContains(searchText) ||
                $0.description.localizedCaseInsensitiveContains(searchText)
            }
        }
        return result
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Template Library")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button(action: {
                    onEditTemplate(nil)
                }) {
                    Label("New Template", systemImage: "plus.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)

                Button("Done") { dismiss() }
            }
            .padding()

            Divider()

            HStack(spacing: 0) {
                // Categories sidebar
                VStack(alignment: .leading, spacing: 4) {
                    Text("Categories")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.top, 8)

                    Button(action: { selectedCategory = nil }) {
                        HStack {
                            Text("All Templates")
                            Spacer()
                            Text("\(templates.count)")
                                .foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(selectedCategory == nil ? .indigo.opacity(0.1) : .clear)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)

                    ForEach(TemplateCategory.allCases, id: \.self) { category in
                        let count = templates.filter { $0.category == category }.count
                        if count > 0 {
                            Button(action: { selectedCategory = category }) {
                                HStack {
                                    Image(systemName: category.icon)
                                        .frame(width: 20)
                                    Text(category.displayName)
                                    Spacer()
                                    Text("\(count)")
                                        .foregroundStyle(.secondary)
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(selectedCategory == category ? .indigo.opacity(0.1) : .clear)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    Spacer()
                }
                .frame(width: 180)
                .padding(.vertical, 8)

                Divider()

                // Templates grid
                VStack(spacing: 0) {
                    // Search
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                        TextField("Search templates...", text: $searchText)
                            .textFieldStyle(.plain)
                    }
                    .padding(8)
                    .background(.quaternary.opacity(0.5))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .padding()

                    ScrollView {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 240))], spacing: 12) {
                            ForEach(filteredTemplates) { template in
                                TemplateCard(
                                    template: template,
                                    onApply: {
                                        Task {
                                            await onApply(template.id)
                                            dismiss()
                                        }
                                    },
                                    onEdit: {
                                        onEditTemplate(template)
                                    },
                                    onDelete: {
                                        Task {
                                            do {
                                                try await InsightsService.shared.deleteTemplate(templateId: template.id)
                                            } catch {
                                                logger.error("Failed to delete template \(template.id): \(error)")
                                            }
                                            await onRefresh()
                                        }
                                    }
                                )
                            }
                        }
                        .padding()
                    }
                }
            }
        }
        .frame(width: 800, height: 550)
    }
}
