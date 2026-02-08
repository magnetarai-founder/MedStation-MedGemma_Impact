//
//  ModelDiscoveryFiltersPane.swift
//  MagnetarStudio (macOS)
//
//  Filters pane for model discovery - Extracted from ModelDiscoveryWorkspace.swift (Phase 6.22)
//

import SwiftUI

struct ModelDiscoveryFiltersPane: View {
    @Binding var searchText: String
    @Binding var selectedModelType: ModelTypeFilter
    @Binding var selectedCapability: CapabilityFilter
    @Binding var sortBy: SortOption
    let currentPage: Int
    let totalCount: Int
    let pageSize: Int
    let isLoading: Bool
    let onSearch: () async -> Void

    var body: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Discover",
                icon: "magnifyingglass"
            )

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Search
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Search")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)

                        TextField("Search models...", text: $searchText)
                            .textFieldStyle(.roundedBorder)
                            .onSubmit {
                                Task { await onSearch() }
                            }

                        Button("Search") {
                            Task { await onSearch() }
                        }
                        .buttonStyle(.bordered)
                        .disabled(isLoading)
                    }

                    Divider()

                    // Model Type
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Type")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)

                        Picker("", selection: $selectedModelType) {
                            ForEach(ModelTypeFilter.allCases, id: \.self) { type in
                                Text(type.displayName).tag(type)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: selectedModelType) { _, _ in
                            Task { await onSearch() }
                        }
                    }

                    Divider()

                    // Capability
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Capability")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)

                        Picker("", selection: $selectedCapability) {
                            ForEach(CapabilityFilter.allCases, id: \.self) { cap in
                                Text(cap.displayName).tag(cap)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: selectedCapability) { _, _ in
                            Task { await onSearch() }
                        }
                    }

                    Divider()

                    // Sort
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Sort By")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)

                        Picker("", selection: $sortBy) {
                            ForEach(SortOption.allCases, id: \.self) { option in
                                Text(option.displayName).tag(option)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.radioGroup)
                        .onChange(of: sortBy) { _, _ in
                            Task { await onSearch() }
                        }
                    }

                    Divider()

                    // Results info
                    if totalCount > 0 {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("\(totalCount) models found")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            Text("Page \(currentPage + 1) of \((totalCount + pageSize - 1) / pageSize)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .padding()
            }
        }
    }
}
