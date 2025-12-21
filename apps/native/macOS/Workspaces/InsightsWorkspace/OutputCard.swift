//
//  OutputCard.swift
//  MagnetarStudio
//
//  Formatted output card for Insights Lab
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

    var outputTemplate: InsightsTemplate? {
        templates.first { $0.id == output.templateId }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "doc.text.fill")
                    .foregroundStyle(.indigo)
                Text(output.templateName)
                    .font(.headline)
                Spacer()
                Text(output.formattedDate)
                    .font(.caption)
                    .foregroundStyle(.secondary)

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
                    }
                }
                .buttonStyle(.plain)
                .help("Regenerate with same template")
                .disabled(isRegenerating)

                Button(action: { isExpanded.toggle() }) {
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                }
                .buttonStyle(.plain)

                Menu {
                    Button("Copy Content") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(output.content, forType: .string)
                    }

                    if let template = outputTemplate, !template.isBuiltin {
                        Button("Refine Template...") {
                            onRefineTemplate(template)
                        }
                    }

                    Button("Export as Markdown...") {
                        exportAsMarkdown()
                    }

                    Divider()
                    Button("Delete", role: .destructive, action: onDelete)
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
                .menuStyle(.borderlessButton)
            }
            .padding()
            .background(.quaternary.opacity(0.3))

            if isExpanded {
                Divider()

                // Content
                ScrollView {
                    Text(output.content)
                        .font(.body)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                }
                .frame(maxHeight: 400)
            }
        }
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(.quaternary, lineWidth: 1)
        )
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
