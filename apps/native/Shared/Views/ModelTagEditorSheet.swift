//
//  ModelTagEditorSheet.swift
//  MagnetarStudio
//
//  Modal for editing model capability tags
//  Shows auto-detected tags + allows manual override
//

import SwiftUI

struct ModelTagEditorSheet: View {
    let modelName: String
    @Environment(\.dismiss) private var dismiss

    @State private var availableTags: [ModelCapabilityTag] = []
    @State private var currentTags: ModelTagsResponse?
    @State private var selectedTags: Set<String> = []
    @State private var isLoading = false
    @State private var isSaving = false
    @State private var errorMessage: String?

    private let tagService = ModelTagService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Edit Model Tags")
                        .font(.headline)

                    Text(modelName)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding()

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 48))
                        .foregroundColor(.red)

                    Text("Error Loading Tags")
                        .font(.headline)

                    Text(error)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)

                    Button("Retry") {
                        Task { await loadData() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        // Current Status
                        if let current = currentTags {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Current Tags")
                                        .font(.subheadline)
                                        .fontWeight(.semibold)

                                    Spacer()

                                    if current.manualOverride {
                                        HStack(spacing: 4) {
                                            Image(systemName: "pencil.circle.fill")
                                                .font(.caption)
                                            Text("Manual Override")
                                                .font(.caption2)
                                        }
                                        .foregroundColor(.orange)
                                    } else {
                                        HStack(spacing: 4) {
                                            Image(systemName: "sparkles")
                                                .font(.caption)
                                            Text("Auto-Detected")
                                                .font(.caption2)
                                        }
                                        .foregroundColor(.green)
                                    }
                                }

                                // Selected tags display
                                FlowLayout(spacing: 8) {
                                    ForEach(current.tags, id: \.self) { tagId in
                                        if let tag = availableTags.first(where: { $0.id == tagId }) {
                                            TagChip(tag: tag, isSelected: true, onTap: {})
                                        }
                                    }
                                }
                            }
                            .padding()
                            .background(Color.surfaceSecondary.opacity(0.3))
                            .cornerRadius(12)
                        }

                        Divider()

                        // Tag Selector - Grouped by Category
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Select Capabilities")
                                .font(.subheadline)
                                .fontWeight(.semibold)

                            ForEach(TagCategory.allCases, id: \.self) { category in
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(category.rawValue)
                                        .font(.caption)
                                        .foregroundColor(.secondary)

                                    FlowLayout(spacing: 8) {
                                        ForEach(category.tags(from: availableTags)) { tag in
                                            TagChip(
                                                tag: tag,
                                                isSelected: selectedTags.contains(tag.id),
                                                onTap: {
                                                    toggleTag(tag.id)
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                    .padding()
                }

                Divider()

                // Footer Actions
                HStack(spacing: 12) {
                    // Revert to Auto button
                    if currentTags?.manualOverride == true {
                        Button(action: { Task { await revertToAuto() } }) {
                            HStack(spacing: 4) {
                                Image(systemName: "sparkles")
                                Text("Revert to Auto")
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .disabled(isSaving)
                    }

                    Spacer()

                    // Cancel
                    Button("Cancel") {
                        dismiss()
                    }
                    .buttonStyle(.bordered)

                    // Save
                    Button(action: { Task { await saveTags() } }) {
                        if isSaving {
                            ProgressView()
                                .scaleEffect(0.8)
                        } else {
                            Text("Save Tags")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(isSaving || selectedTags == Set(currentTags?.tags ?? []))
                }
                .padding()
            }
        }
        .frame(width: 550, height: 600)
        .background(Color.surfacePrimary)
        .task {
            await loadData()
        }
    }

    // MARK: - Actions

    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            // Load available tags and current model tags in parallel
            async let tagsTask = tagService.getAvailableTags()
            async let currentTask = tagService.getModelTags(modelName: modelName)

            availableTags = try await tagsTask
            currentTags = try await currentTask
            selectedTags = Set(currentTags?.tags ?? [])
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    private func toggleTag(_ tagId: String) {
        if selectedTags.contains(tagId) {
            selectedTags.remove(tagId)
        } else {
            selectedTags.insert(tagId)
        }
    }

    private func saveTags() async {
        isSaving = true

        do {
            let updated = try await tagService.updateModelTags(
                modelName: modelName,
                tags: Array(selectedTags)
            )
            currentTags = updated
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }

        isSaving = false
    }

    private func revertToAuto() async {
        isSaving = true

        do {
            let updated = try await tagService.deleteTagOverrides(modelName: modelName)
            currentTags = updated
            selectedTags = Set(updated.tags)
        } catch {
            errorMessage = error.localizedDescription
        }

        isSaving = false
    }
}

// MARK: - Tag Chip Component

struct TagChip: View {
    let tag: ModelCapabilityTag
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 6) {
                Image(systemName: tag.icon)
                    .font(.caption2)
                Text(tag.name)
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(isSelected ? tag.color.opacity(0.2) : Color.surfaceSecondary)
            .foregroundColor(isSelected ? tag.color : .textSecondary)
            .cornerRadius(16)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(isSelected ? tag.color.opacity(0.4) : Color.clear, lineWidth: 1.5)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Flow Layout (wrap tags)

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(
            in: proposal.replacingUnspecifiedDimensions().width,
            subviews: subviews,
            spacing: spacing
        )
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(
            in: bounds.width,
            subviews: subviews,
            spacing: spacing
        )
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x, y: bounds.minY + result.positions[index].y), proposal: .unspecified)
        }
    }

    struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []

        init(in maxWidth: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var currentX: CGFloat = 0
            var currentY: CGFloat = 0
            var lineHeight: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)

                if currentX + size.width > maxWidth && currentX > 0 {
                    currentX = 0
                    currentY += lineHeight + spacing
                    lineHeight = 0
                }

                positions.append(CGPoint(x: currentX, y: currentY))
                currentX += size.width + spacing
                lineHeight = max(lineHeight, size.height)
            }

            self.size = CGSize(width: maxWidth, height: currentY + lineHeight)
        }
    }
}

// MARK: - Preview

#Preview {
    ModelTagEditorSheet(modelName: "qwen2.5-coder:7b")
}
