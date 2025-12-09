//
//  ModelDiscoveryDetailPane.swift
//  MagnetarStudio (macOS)
//
//  Model detail pane with download - Extracted from ModelDiscoveryWorkspace.swift (Phase 6.22)
//

import SwiftUI

struct ModelDiscoveryDetailPane: View {
    let selectedModel: LibraryModel?
    let downloadingModel: String?
    let downloadProgress: String?
    let onDownload: (LibraryModel) async -> Void

    var body: some View {
        Group {
            if let model = selectedModel {
                VStack(spacing: 0) {
                    // Model header
                    HStack(spacing: 16) {
                        Image(systemName: model.isOfficial ? "checkmark.seal.fill" : "cube.box.fill")
                            .font(.system(size: 56))
                            .foregroundStyle(
                                model.isOfficial
                                    ? LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
                                    : LinearGradient.magnetarGradient
                            )

                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 8) {
                                Text(model.modelName)
                                    .font(.title2)
                                    .fontWeight(.bold)

                                if model.isOfficial {
                                    Text("OFFICIAL")
                                        .font(.caption2)
                                        .fontWeight(.bold)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.blue.opacity(0.2))
                                        .foregroundColor(.blue)
                                        .cornerRadius(4)
                                }
                            }

                            HStack(spacing: 8) {
                                HStack(spacing: 4) {
                                    Image(systemName: "arrow.down.circle.fill")
                                        .font(.caption2)
                                        .foregroundColor(.green)
                                    Text("\(model.pullsFormatted) pulls")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }

                                if !model.labelsText.isEmpty {
                                    Text("•")
                                        .foregroundColor(.secondary)

                                    Text(model.labelsText)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            if let capability = model.capability {
                                Text(capability.capitalized)
                                    .font(.caption2)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color.purple.opacity(0.2))
                                    .foregroundColor(.purple)
                                    .cornerRadius(4)
                            }
                        }

                        Spacer()
                    }
                    .padding(24)
                    .background(Color.surfaceTertiary.opacity(0.3))

                    Divider()

                    // Model details and actions
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            // Download action
                            VStack(spacing: 12) {
                                if downloadingModel == model.modelIdentifier {
                                    // Downloading
                                    VStack(spacing: 8) {
                                        HStack(spacing: 8) {
                                            ProgressView()
                                                .scaleEffect(0.8)
                                            Text(downloadProgress ?? "Downloading...")
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }
                                        .padding(12)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color.surfaceSecondary.opacity(0.5))
                                        .cornerRadius(8)
                                    }
                                } else {
                                    // Download button
                                    Button(action: {
                                        Task {
                                            await onDownload(model)
                                        }
                                    }) {
                                        Label("Download Model", systemImage: "arrow.down.circle")
                                            .frame(maxWidth: .infinity)
                                    }
                                    .buttonStyle(.borderedProminent)
                                }
                            }

                            // Description
                            if let description = model.description, !description.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Description")
                                        .font(.headline)

                                    Text(description)
                                        .font(.body)
                                        .foregroundColor(.secondary)
                                }
                            }

                            // Tags
                            if !model.tags.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Available Tags")
                                        .font(.headline)

                                    FlowLayout(spacing: 8) {
                                        ForEach(model.tags, id: \.self) { tag in
                                            Text(tag)
                                                .font(.caption)
                                                .padding(.horizontal, 8)
                                                .padding(.vertical, 4)
                                                .background(Color.secondary.opacity(0.2))
                                                .foregroundColor(.secondary)
                                                .cornerRadius(4)
                                        }
                                    }
                                }
                            }

                            // Link to Ollama
                            if let url = URL(string: model.url) {
                                Button {
                                    NSWorkspace.shared.open(url)
                                } label: {
                                    Label("View on Ollama.com", systemImage: "arrow.up.right.square")
                                }
                                .buttonStyle(.link)
                            }
                        }
                        .padding()
                    }
                }
            } else {
                PaneEmptyState(
                    icon: "cube.box",
                    title: "Select a model",
                    subtitle: "Browse and download models from Ollama library"
                )
            }
        }
    }
}
