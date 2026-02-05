//
//  OutputCard.swift
//  MagnetarStudio
//
//  Formatted output card for Insights Lab
//  Enhanced with copy feedback, word count, and better visual hierarchy
//

import SwiftUI
import AppKit

struct OutputCard: View {
    let output: FormattedOutput
    let templates: [InsightsTemplate]
    let onDelete: () -> Void
    let onRegenerate: () async -> Void
    let onRefineTemplate: (InsightsTemplate) -> Void

    @State private var isExpanded = true
    @State private var isRegenerating = false
    @State private var showCopied = false
    @State private var copyResetTask: Task<Void, Never>?
    @State private var isHovered = false

    var outputTemplate: InsightsTemplate? {
        templates.first { $0.id == output.templateId }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            headerView
                .padding()
                .background(.quaternary.opacity(0.3))

            if isExpanded {
                Divider()

                // Content
                contentView
            }

            // Footer with metadata
            if isExpanded {
                Divider()
                footerView
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(.quaternary.opacity(0.15))
            }
        }
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.indigo.opacity(0.3) : Color.gray.opacity(0.2), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    // MARK: - Header

    private var headerView: some View {
        HStack(spacing: 12) {
            // Template icon based on format
            ZStack {
                Circle()
                    .fill(Color.indigo.opacity(0.1))
                    .frame(width: 36, height: 36)

                Image(systemName: formatIcon)
                    .font(.system(size: 16))
                    .foregroundStyle(.indigo)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(output.templateName)
                    .font(.headline)

                Text(output.relativeDate)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // Quick copy button
            Button(action: copyContent) {
                HStack(spacing: 4) {
                    Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 12))
                    if showCopied {
                        Text("Copied!")
                            .font(.caption)
                    }
                }
                .foregroundColor(showCopied ? .green : .secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    Capsule()
                        .fill(showCopied ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                )
            }
            .buttonStyle(.plain)
            .help("Copy to clipboard")

            // Regenerate button
            Button(action: {
                Task {
                    isRegenerating = true
                    await onRegenerate()
                    isRegenerating = false
                }
            }) {
                if isRegenerating {
                    ProgressView()
                        .controlSize(.small)
                } else {
                    Image(systemName: "arrow.clockwise")
                        .foregroundColor(.secondary)
                }
            }
            .buttonStyle(.plain)
            .help("Regenerate with same template")
            .disabled(isRegenerating)

            // Expand/collapse
            Button(action: {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isExpanded.toggle()
                }
            }) {
                Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)

            // More options
            Menu {
                Button(action: copyContent) {
                    Label("Copy Content", systemImage: "doc.on.doc")
                }

                if let template = outputTemplate, !template.isBuiltin {
                    Button {
                        onRefineTemplate(template)
                    } label: {
                        Label("Refine Template...", systemImage: "pencil")
                    }
                }

                Button(action: exportAsMarkdown) {
                    Label("Export as Markdown...", systemImage: "square.and.arrow.up")
                }

                Divider()
                Button(role: .destructive, action: onDelete) {
                    Label("Delete", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .foregroundColor(.secondary)
            }
            .menuStyle(.borderlessButton)
        }
    }

    // MARK: - Content

    private var contentView: some View {
        ScrollView {
            Text(output.content)
                .font(.body)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
        }
        .frame(maxHeight: 400)
    }

    // MARK: - Footer

    private var footerView: some View {
        HStack(spacing: 16) {
            // Word count
            Label(output.formattedWordCount, systemImage: "text.word.spacing")
                .font(.caption)
                .foregroundStyle(.secondary)

            // Format badge
            HStack(spacing: 4) {
                Image(systemName: formatIcon)
                    .font(.system(size: 10))
                Text(output.format.displayName)
                    .font(.caption)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Color.indigo.opacity(0.1))
            .foregroundStyle(.indigo)
            .clipShape(Capsule())

            Spacer()

            // Full date on hover
            if isHovered {
                Text(output.formattedDate)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .transition(.opacity)
            }
        }
    }

    // MARK: - Helpers

    private var formatIcon: String {
        switch output.format {
        case .markdown: return "text.document"
        case .text: return "doc.text"
        case .json: return "curlybraces"
        case .html: return "chevron.left.forwardslash.chevron.right"
        }
    }

    private func copyContent() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(output.content, forType: .string)

        withAnimation {
            showCopied = true
        }

        copyResetTask?.cancel()
        copyResetTask = Task {
            try? await Task.sleep(for: .seconds(1.5))
            guard !Task.isCancelled else { return }
            withAnimation { showCopied = false }
        }
    }

    private func exportAsMarkdown() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.text]
        panel.nameFieldStringValue = "\(output.templateName).md"

        if panel.runModal() == .OK, let url = panel.url {
            try? output.content.write(to: url, atomically: true, encoding: .utf8)
        }
    }
}
