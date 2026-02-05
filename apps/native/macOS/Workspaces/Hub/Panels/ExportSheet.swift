//
//  ExportSheet.swift
//  MagnetarStudio (macOS)
//
//  Export dialog — format picker, options, live preview, and save.
//  Used by Notes, Docs, and Sheets panels.
//

import SwiftUI

struct ExportSheet: View {
    let content: ExportContent
    let onDismiss: () -> Void

    @State private var options = ExportOptions()
    @State private var previewText = ""
    @State private var isExporting = false
    @State private var exportError: String?

    private var availableFormats: [DocumentExportFormat] {
        switch content {
        case .spreadsheet:
            return DocumentExportFormat.allCases
        case .blocks, .plainText:
            return [.pdf, .markdown, .html]
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Body
            HStack(spacing: 0) {
                // Options panel
                optionsPanel
                    .frame(width: 240)

                Divider()

                // Preview
                previewPanel
            }

            Divider()

            // Footer
            footer
        }
        .frame(width: 720, height: 480)
        .onAppear {
            // Default to first available format
            if !availableFormats.contains(options.format) {
                options.format = availableFormats.first ?? .pdf
            }
            updatePreview()
        }
        .onChange(of: options.format) { _, _ in updatePreview() }
        .onChange(of: options.includeTitle) { _, _ in updatePreview() }
        .onChange(of: options.fontSize) { _, _ in updatePreview() }
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Image(systemName: "arrow.up.doc")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
            Text("Export")
                .font(.system(size: 14, weight: .semibold))

            Spacer()

            Button {
                onDismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    // MARK: - Options Panel

    private var optionsPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Format picker
                VStack(alignment: .leading, spacing: 8) {
                    Text("Format")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    ForEach(availableFormats) { format in
                        formatRow(format)
                    }
                }

                Divider()

                // Options
                VStack(alignment: .leading, spacing: 10) {
                    Text("Options")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    Toggle("Include title", isOn: $options.includeTitle)
                        .font(.system(size: 13))

                    if options.format == .pdf {
                        Toggle("Page numbers", isOn: $options.includePageNumbers)
                            .font(.system(size: 13))

                        Picker("Page size", selection: $options.pageSize) {
                            ForEach(ExportPageSize.allCases) { size in
                                Text(size.rawValue).tag(size)
                            }
                        }
                        .font(.system(size: 13))
                    }

                    if options.format == .html || options.format == .pdf {
                        HStack {
                            Text("Font size")
                                .font(.system(size: 13))
                            Spacer()
                            Stepper("\(Int(options.fontSize))px", value: $options.fontSize, in: 8...24, step: 1)
                                .font(.system(size: 12))
                        }
                    }
                }
            }
            .padding(16)
        }
    }

    private func formatRow(_ format: DocumentExportFormat) -> some View {
        Button {
            options.format = format
        } label: {
            HStack(spacing: 10) {
                Image(systemName: format.icon)
                    .font(.system(size: 13))
                    .foregroundStyle(options.format == format ? .white : .secondary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 1) {
                    Text(format.rawValue)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(options.format == format ? .white : .primary)
                    Text(".\(format.fileExtension)")
                        .font(.system(size: 10))
                        .foregroundStyle(options.format == format ? .white.opacity(0.7) : .secondary)
                }

                Spacer()

                if options.format == format {
                    Image(systemName: "checkmark")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.white)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(options.format == format ? Color.accentColor : Color.clear)
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Preview Panel

    private var previewPanel: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Preview header
            HStack {
                Text("Preview")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)
                Spacer()
                Text(options.format.rawValue)
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            Divider()

            // Preview content
            ScrollView {
                Text(previewText)
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.primary)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
            }
            .background(Color.surfacePrimary)
        }
    }

    // MARK: - Footer

    private var footer: some View {
        HStack {
            if let exportError {
                Image(systemName: "exclamationmark.triangle")
                    .foregroundStyle(.red)
                Text(exportError)
                    .font(.system(size: 11))
                    .foregroundStyle(.red)
                    .lineLimit(1)
            }

            Spacer()

            Button("Cancel") {
                onDismiss()
            }
            .keyboardShortcut(.cancelAction)

            Button {
                Task { await performExport() }
            } label: {
                if isExporting {
                    ProgressView()
                        .controlSize(.small)
                        .padding(.horizontal, 8)
                } else {
                    Text("Export")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(isExporting)
            .keyboardShortcut(.defaultAction)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Actions

    private func updatePreview() {
        do {
            previewText = try ExportService.shared.preview(content: content, options: options)
        } catch {
            previewText = "Preview unavailable: \(error.localizedDescription)"
        }
    }

    private func performExport() async {
        isExporting = true
        exportError = nil

        do {
            _ = try await ExportService.shared.export(content: content, options: options)
            onDismiss()
        } catch let error as ExportError {
            if case .saveFailed("Export cancelled") = error {
                // User cancelled save panel — not an error
            } else {
                exportError = error.localizedDescription
            }
        } catch {
            exportError = error.localizedDescription
        }

        isExporting = false
    }
}
