//
//  ExportService.swift
//  MagnetarStudio
//
//  Exports workspace content (notes, docs, sheets) to PDF, Markdown, HTML, CSV.
//  @MainActor singleton — all export operations run on main thread for NSPrintOperation.
//

import Foundation
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ExportService")

@MainActor
final class ExportService {
    static let shared = ExportService()
    private init() {}

    // MARK: - Plugin Export Formats

    /// Available plugin-provided export formats.
    var pluginExportFormats: [RegisteredExportFormat] {
        PluginRegistry.shared.exportFormats
    }

    /// Export content using a plugin-provided format handler.
    func exportViaPlugin(formatId: String, content: String, title: String) async throws -> URL {
        guard let handler = PluginRegistry.shared.exportHandler(for: formatId) else {
            throw ExportError.renderingFailed("No plugin handler for format: \(formatId)")
        }
        let data = try await handler.export(content: content, title: title)
        let url = try await showSavePanel(
            defaultName: "\(sanitizeFilename(title)).\(handler.fileExtension)",
            fileExtension: handler.fileExtension
        )
        try data.write(to: url, options: .atomic)
        logger.debug("[Export] Plugin export '\(handler.formatName)' saved to \(url.lastPathComponent)")
        return url
    }

    // MARK: - Public API

    /// Export content to a file in the given format. Returns the saved URL.
    func export(content: ExportContent, options: ExportOptions) async throws -> URL {
        let data: Data
        let defaultName: String

        switch content {
        case .blocks(let blocks, let title):
            defaultName = sanitizeFilename(title)
            data = try renderBlocks(blocks, title: title, options: options)

        case .spreadsheet(let doc):
            defaultName = sanitizeFilename(doc.title)
            data = try renderSpreadsheet(doc, options: options)

        case .plainText(let text, let title):
            defaultName = sanitizeFilename(title)
            data = try renderPlainText(text, title: title, options: options)
        }

        let url = try await showSavePanel(
            defaultName: "\(defaultName).\(options.format.fileExtension)",
            fileExtension: options.format.fileExtension
        )

        try data.write(to: url, options: .atomic)
        logger.debug("[Export] Saved \(options.format.rawValue) to \(url.lastPathComponent)")
        return url
    }

    /// Generate preview data without saving.
    func preview(content: ExportContent, options: ExportOptions) throws -> String {
        switch options.format {
        case .markdown:
            return previewMarkdown(content: content, options: options)
        case .html:
            return previewHTML(content: content, options: options)
        case .csv:
            return previewCSV(content: content)
        case .pdf:
            return "[PDF Preview]"
        }
    }

    // MARK: - Block Rendering

    private func renderBlocks(_ blocks: [DocumentBlock], title: String, options: ExportOptions) throws -> Data {
        switch options.format {
        case .markdown:
            let md = MarkdownRenderer.render(blocks: blocks, title: title, includeTitle: options.includeTitle)
            guard let data = md.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode Markdown")
            }
            return data

        case .html:
            let html = HTMLRenderer.render(blocks: blocks, title: title, includeTitle: options.includeTitle, fontSize: options.fontSize)
            guard let data = html.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode HTML")
            }
            return data

        case .pdf:
            let html = HTMLRenderer.render(blocks: blocks, title: title, includeTitle: options.includeTitle, fontSize: options.fontSize)
            return try renderHTMLToPDF(html: html, pageSize: options.pageSize)

        case .csv:
            throw ExportError.unsupportedFormat(.csv, "documents")
        }
    }

    // MARK: - Spreadsheet Rendering

    private func renderSpreadsheet(_ doc: SpreadsheetDocument, options: ExportOptions) throws -> Data {
        switch options.format {
        case .csv:
            let csv = CSVRenderer.render(spreadsheet: doc, includeTitle: options.includeTitle)
            guard let data = csv.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode CSV")
            }
            return data

        case .html:
            let html = renderSpreadsheetHTML(doc, includeTitle: options.includeTitle)
            guard let data = html.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode HTML")
            }
            return data

        case .pdf:
            let html = renderSpreadsheetHTML(doc, includeTitle: options.includeTitle)
            return try renderHTMLToPDF(html: html, pageSize: options.pageSize)

        case .markdown:
            let md = renderSpreadsheetMarkdown(doc, includeTitle: options.includeTitle)
            guard let data = md.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode Markdown")
            }
            return data
        }
    }

    // MARK: - Plain Text Rendering

    private func renderPlainText(_ text: String, title: String, options: ExportOptions) throws -> Data {
        switch options.format {
        case .markdown:
            var md = ""
            if options.includeTitle { md += "# \(title)\n\n" }
            md += text
            guard let data = md.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode text")
            }
            return data

        case .html:
            let escaped = text.replacingOccurrences(of: "<", with: "&lt;")
                .replacingOccurrences(of: ">", with: "&gt;")
            let safeTitle = escapeHTML(title)
            let titleHTML = options.includeTitle ? "<h1>\(safeTitle)</h1>" : ""
            let html = """
            <!DOCTYPE html>
            <html><head><meta charset="UTF-8"><title>\(safeTitle)</title>
            <style>body{font-family:-apple-system,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;}</style>
            </head><body>\(titleHTML)<pre>\(escaped)</pre></body></html>
            """
            guard let data = html.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode HTML")
            }
            return data

        case .pdf:
            let safeTitle2 = escapeHTML(title)
            let titleHTML = options.includeTitle ? "<h1>\(safeTitle2)</h1>" : ""
            let escaped = text.replacingOccurrences(of: "<", with: "&lt;")
            let html = """
            <!DOCTYPE html>
            <html><head><meta charset="UTF-8">
            <style>body{font-family:-apple-system,sans-serif;padding:40px;}</style>
            </head><body>\(titleHTML)<pre>\(escaped)</pre></body></html>
            """
            return try renderHTMLToPDF(html: html, pageSize: options.pageSize)

        case .csv:
            guard let data = text.data(using: .utf8) else {
                throw ExportError.renderingFailed("Failed to encode CSV")
            }
            return data
        }
    }

    // MARK: - Spreadsheet Renderers

    private func renderSpreadsheetHTML(_ doc: SpreadsheetDocument, includeTitle: Bool) -> String {
        var maxRow = 0
        var maxCol = 0
        for key in doc.cells.keys {
            if let addr = CellAddress.fromString(key) {
                maxRow = max(maxRow, addr.row)
                maxCol = max(maxCol, addr.column)
            }
        }

        var rows: [String] = []

        // Header row (column letters)
        var headerCells = "<th></th>"
        for col in 0...maxCol {
            headerCells += "<th>\(CellAddress.columnLetter(col))</th>"
        }
        rows.append("<tr>\(headerCells)</tr>")

        // Data rows
        for row in 0...maxRow {
            var cells = "<td class=\"row-num\">\(row + 1)</td>"
            for col in 0...maxCol {
                let addr = CellAddress(column: col, row: row)
                let cell = doc.cell(at: addr)
                let value = cell.rawValue
                    .replacingOccurrences(of: "<", with: "&lt;")
                    .replacingOccurrences(of: ">", with: "&gt;")
                let style = cellStyle(cell)
                cells += "<td\(style)>\(value)</td>"
            }
            rows.append("<tr>\(cells)</tr>")
        }

        let safeDocTitle = escapeHTML(doc.title)
        let titleHTML = includeTitle ? "<h1>\(safeDocTitle)</h1>" : ""
        return """
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>\(safeDocTitle)</title>
        <style>
        body{font-family:-apple-system,sans-serif;padding:20px;}
        table{border-collapse:collapse;width:100%;}
        th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:13px;}
        th{background:#f5f5f5;font-weight:600;font-size:12px;}
        .row-num{background:#f5f5f5;font-weight:600;font-size:12px;width:40px;text-align:center;}
        </style>
        </head><body>\(titleHTML)<table>\(rows.joined(separator: "\n"))</table></body></html>
        """
    }

    private func renderSpreadsheetMarkdown(_ doc: SpreadsheetDocument, includeTitle: Bool) -> String {
        var maxRow = 0
        var maxCol = 0
        for key in doc.cells.keys {
            if let addr = CellAddress.fromString(key) {
                maxRow = max(maxRow, addr.row)
                maxCol = max(maxCol, addr.column)
            }
        }

        var lines: [String] = []
        if includeTitle { lines.append("# \(doc.title)\n") }

        // Header
        var header = "|"
        var separator = "|"
        for col in 0...maxCol {
            header += " \(CellAddress.columnLetter(col)) |"
            separator += " --- |"
        }
        lines.append(header)
        lines.append(separator)

        // Data rows
        for row in 0...maxRow {
            var rowStr = "|"
            for col in 0...maxCol {
                let addr = CellAddress(column: col, row: row)
                let cell = doc.cell(at: addr)
                rowStr += " \(cell.rawValue) |"
            }
            lines.append(rowStr)
        }

        return lines.joined(separator: "\n")
    }

    private func cellStyle(_ cell: SpreadsheetCell) -> String {
        var styles: [String] = []
        if cell.isBold { styles.append("font-weight:bold") }
        if cell.isItalic { styles.append("font-style:italic") }
        switch cell.alignment {
        case .center: styles.append("text-align:center")
        case .right: styles.append("text-align:right")
        case .left: break
        }
        return styles.isEmpty ? "" : " style=\"\(styles.joined(separator: ";"))\""
    }

    // MARK: - PDF Rendering

    private func renderHTMLToPDF(html: String, pageSize: ExportPageSize) throws -> Data {
        guard let htmlData = html.data(using: .utf8) else {
            throw ExportError.renderingFailed("Failed to encode HTML for PDF")
        }
        guard let attrString = NSAttributedString(
            html: htmlData,
            documentAttributes: nil
        ) else {
            throw ExportError.renderingFailed("Failed to parse HTML for PDF")
        }

        let printInfo = NSPrintInfo()
        printInfo.paperSize = pageSize.size
        printInfo.topMargin = 36
        printInfo.bottomMargin = 36
        printInfo.leftMargin = 36
        printInfo.rightMargin = 36

        let textView = NSTextView(frame: NSRect(
            x: 0, y: 0,
            width: pageSize.size.width - 72,
            height: pageSize.size.height - 72
        ))
        textView.textStorage?.setAttributedString(attrString)

        let printOp = NSPrintOperation(view: textView, printInfo: printInfo)
        printOp.showsPrintPanel = false
        printOp.showsProgressPanel = false

        // Use PDF output
        printInfo.jobDisposition = .save
        printInfo.dictionary()[NSPrintInfo.AttributeKey.jobSavingURL] = URL(fileURLWithPath: "/dev/null")

        // Generate via print-to-PDF
        guard let pdfRep = textView.dataWithPDF(inside: textView.bounds) as Data? else {
            throw ExportError.renderingFailed("PDF generation failed")
        }

        return pdfRep
    }

    // MARK: - Preview Helpers

    private func previewMarkdown(content: ExportContent, options: ExportOptions) -> String {
        switch content {
        case .blocks(let blocks, let title):
            return MarkdownRenderer.render(blocks: blocks, title: title, includeTitle: options.includeTitle)
        case .spreadsheet(let doc):
            return renderSpreadsheetMarkdown(doc, includeTitle: options.includeTitle)
        case .plainText(let text, let title):
            var result = ""
            if options.includeTitle { result += "# \(title)\n\n" }
            result += text
            return result
        }
    }

    private func previewHTML(content: ExportContent, options: ExportOptions) -> String {
        switch content {
        case .blocks(let blocks, let title):
            return HTMLRenderer.render(blocks: blocks, title: title, includeTitle: options.includeTitle, fontSize: options.fontSize)
        case .spreadsheet(let doc):
            return renderSpreadsheetHTML(doc, includeTitle: options.includeTitle)
        case .plainText(let text, let title):
            return "<h1>\(escapeHTML(title))</h1><pre>\(escapeHTML(text))</pre>"
        }
    }

    private func previewCSV(content: ExportContent) -> String {
        switch content {
        case .spreadsheet(let doc):
            return CSVRenderer.render(spreadsheet: doc)
        case .blocks(_, let title):
            return "CSV export not supported for documents (\(title))"
        case .plainText(let text, _):
            return text
        }
    }

    // MARK: - Save Panel

    private func showSavePanel(defaultName: String, fileExtension: String) async throws -> URL {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = defaultName
        panel.allowedContentTypes = [.init(filenameExtension: fileExtension)].compactMap { $0 }
        panel.canCreateDirectories = true

        let response = panel.runModal()
        guard response == .OK, let url = panel.url else {
            throw ExportError.saveFailed("Export cancelled")
        }
        return url
    }

    // MARK: - Utilities

    private func sanitizeFilename(_ name: String) -> String {
        let cleaned = name.components(separatedBy: CharacterSet.alphanumerics.union(.whitespaces).inverted).joined()
        let trimmed = cleaned.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? "Untitled" : trimmed.replacingOccurrences(of: " ", with: "_")
    }

    private func escapeHTML(_ str: String) -> String {
        str.replacingOccurrences(of: "&", with: "&amp;")
           .replacingOccurrences(of: "<", with: "&lt;")
           .replacingOccurrences(of: ">", with: "&gt;")
           .replacingOccurrences(of: "\"", with: "&quot;")
    }
}
