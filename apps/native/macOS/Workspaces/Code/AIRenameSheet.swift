//
//  AIRenameSheet.swift
//  MagnetarStudio (macOS)
//
//  Right-click context menu "AI Rename Symbol" — suggests better names with reasoning.
//  Uses WorkspaceAIService.generateSync() for batch suggestion generation.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AIRename")

struct AIRenameSheet: View {
    let originalName: String
    let codeContext: String
    let language: String
    let onRename: (String) -> Void
    let onDismiss: () -> Void

    @State private var suggestions: [RenameSuggestion] = []
    @State private var isLoading = true
    @State private var customName = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "pencil.line")
                    .foregroundStyle(Color.accentColor)
                Text("Rename Symbol")
                    .font(.system(size: 13, weight: .semibold))
                Spacer()
                Button {
                    onDismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Current name
            HStack(spacing: 6) {
                Text("Current:")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                Text(originalName)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundStyle(.primary)
            }

            Divider()

            if isLoading {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.6)
                    Text("Generating suggestions...")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            } else {
                // Suggestions
                ForEach(suggestions) { suggestion in
                    Button {
                        onRename(suggestion.name)
                    } label: {
                        HStack(spacing: 8) {
                            Text(suggestion.name)
                                .font(.system(size: 12, weight: .medium, design: .monospaced))
                                .foregroundStyle(.primary)

                            Spacer()

                            Text(suggestion.reasoning)
                                .font(.system(size: 10))
                                .foregroundStyle(.tertiary)
                                .lineLimit(1)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 6)
                        .background(RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.04)))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }

            Divider()

            // Custom name input
            HStack(spacing: 6) {
                TextField("Custom name...", text: $customName)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12, design: .monospaced))
                    .padding(6)
                    .background(RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.04)))
                    .onSubmit {
                        if !customName.isEmpty {
                            onRename(customName)
                        }
                    }

                Button("Apply") {
                    onRename(customName)
                }
                .controlSize(.small)
                .disabled(customName.isEmpty)
            }
        }
        .padding(14)
        .frame(width: 360)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .shadow(color: .black.opacity(0.2), radius: 8, y: 4)
        .onAppear { generateSuggestions() }
    }

    private func generateSuggestions() {
        Task { @MainActor in
            let aiService = WorkspaceAIService.shared
            let prompt = """
            Suggest 3-5 better names for the \(language) identifier "\(originalName)".
            Context code:
            ```\(language)
            \(String(codeContext.prefix(500)))
            ```

            Return ONLY lines in format: name|reason (one per line).
            """

            let response = await aiService.generateSync(
                action: .askAI,
                input: prompt,
                strategy: TextAIStrategy()
            )

            let parsed = response.components(separatedBy: "\n")
                .filter { $0.contains("|") }
                .prefix(5)
                .map { line -> RenameSuggestion in
                    let parts = line.split(separator: "|", maxSplits: 1)
                    let name = parts.first.map(String.init)?.trimmingCharacters(in: .whitespaces) ?? ""
                    let reason = parts.count > 1 ? String(parts[1]).trimmingCharacters(in: .whitespaces) : ""
                    return RenameSuggestion(name: name, reasoning: reason)
                }

            suggestions = Array(parsed)
            isLoading = false
        }
    }
}

// MARK: - Model

private struct RenameSuggestion: Identifiable {
    let id = UUID()
    let name: String
    let reasoning: String
}
