//
//  ModelDiscoveryListPane.swift
//  MagnetarStudio (macOS)
//
//  Model list pane with pagination - Extracted from ModelDiscoveryWorkspace.swift (Phase 6.22)
//

import SwiftUI

struct ModelDiscoveryListPane: View {
    let libraryModels: [LibraryModel]
    let selectedModel: LibraryModel?
    let isLoading: Bool
    let error: String?
    let downloadingModel: String?
    let currentPage: Int
    let totalCount: Int
    let pageSize: Int
    let onSelectModel: (LibraryModel) -> Void
    let onRetry: () async -> Void
    let onPreviousPage: () -> Void
    let onNextPage: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Models",
                icon: "square.stack.3d.up"
            )

            Divider()

            if isLoading && libraryModels.isEmpty {
                // Loading state
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.5)
                    Text("Loading models...")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = error {
                // Error state
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 48))
                        .foregroundColor(.red)

                    Text("Failed to load models")
                        .font(.system(size: 18, weight: .semibold))

                    Text(error)
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)

                    Button("Try Again") {
                        Task { await onRetry() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding()
            } else if libraryModels.isEmpty {
                PaneEmptyState(
                    icon: "magnifyingglass",
                    title: "No models found",
                    subtitle: "Try adjusting your search or filters"
                )
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(libraryModels) { model in
                            LibraryModelRow(
                                model: model,
                                isSelected: selectedModel?.id == model.id,
                                isDownloading: downloadingModel == model.modelIdentifier
                            )
                            .onTapGesture {
                                onSelectModel(model)
                            }
                        }
                    }
                }

                // Pagination
                if totalCount > pageSize {
                    Divider()

                    HStack(spacing: 12) {
                        Button {
                            onPreviousPage()
                        } label: {
                            Image(systemName: "chevron.left")
                        }
                        .disabled(currentPage == 0 || isLoading)

                        Text("Page \(currentPage + 1)")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Button {
                            onNextPage()
                        } label: {
                            Image(systemName: "chevron.right")
                        }
                        .disabled(currentPage >= (totalCount / pageSize) || isLoading)
                    }
                    .padding()
                }
            }
        }
    }
}
