//
//  HotSlotModelPicker.swift
//  MedStation (macOS)
//
//  Model picker components for hot slots - Extracted from HotSlotSettingsView.swift (Phase 6.24)
//

import SwiftUI

struct ModelPickerSheet: View {
    let slotNumber: Int
    let availableModels: [OllamaModel]
    let onSelect: (String) -> Void
    let onCancel: () -> Void

    @State private var searchText: String = ""

    var filteredModels: [OllamaModel] {
        if searchText.isEmpty {
            return availableModels
        }
        return availableModels.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Assign to Slot \(slotNumber)")
                    .font(.title2)
                    .fontWeight(.bold)

                Spacer()

                Button {
                    onCancel()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(20)

            Divider()

            // Search bar
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)

                TextField("Search models...", text: $searchText)
                    .textFieldStyle(.plain)

                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(12)
            .background(Color.surfaceSecondary.opacity(0.3))
            .cornerRadius(8)
            .padding(.horizontal, 20)
            .padding(.top, 16)

            // Model list
            if filteredModels.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "cube.box")
                        .font(.system(size: 48))
                        .foregroundStyle(.secondary)

                    Text(searchText.isEmpty ? "No models installed" : "No matching models")
                        .font(.headline)
                        .foregroundStyle(.secondary)

                    if searchText.isEmpty {
                        Text("Install models from MedStationHub first")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(filteredModels) { model in
                            ModelPickerRow(model: model) {
                                onSelect(model.name)
                            }
                        }
                    }
                    .padding(20)
                }
            }
        }
        .frame(width: 500, height: 600)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - Model Picker Row

struct ModelPickerRow: View {
    let model: OllamaModel
    let onSelect: () -> Void

    @State private var isHovered: Bool = false

    var body: some View {
        Button {
            onSelect()
        } label: {
            HStack(spacing: 12) {
                // Icon
                Image(systemName: "cube.fill")
                    .font(.title2)
                    .foregroundStyle(LinearGradient.medstationGradient)
                    .frame(width: 40)

                // Model info
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.name)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.primary)

                    HStack(spacing: 8) {
                        if let family = model.details?.family {
                            Text(family.capitalized)
                                .font(.system(size: 11))
                                .foregroundStyle(.secondary)
                        }

                        Text(model.sizeFormatted)
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                // Assign button
                Image(systemName: "arrow.right.circle.fill")
                    .font(.title3)
                    .foregroundStyle(Color.medstationPrimary)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isHovered ? Color.surfaceSecondary.opacity(0.5) : Color.surfaceSecondary.opacity(0.3))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isHovered ? Color.medstationPrimary.opacity(0.5) : Color.clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}
