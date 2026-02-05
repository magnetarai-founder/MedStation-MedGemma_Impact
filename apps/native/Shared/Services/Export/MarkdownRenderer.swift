//
//  MarkdownRenderer.swift
//  MagnetarStudio
//
//  Converts WorkspaceEditor DocumentBlock arrays to Markdown and HTML strings.
//  Handles all 14 block types defined in BlockType.
//

import Foundation

// MARK: - Markdown Renderer

struct MarkdownRenderer {

    /// Convert an array of DocumentBlocks to a Markdown string.
    static func render(blocks: [DocumentBlock], title: String? = nil, includeTitle: Bool = true) -> String {
        var lines: [String] = []
        var numberedListCounter = 0

        if includeTitle, let title, !title.isEmpty {
            lines.append("# \(title)")
            lines.append("")
        }

        for block in blocks {
            // Reset numbered list counter when leaving numbered list context
            if block.type != .numberedList {
                numberedListCounter = 0
            }

            let rendered = renderBlock(block, numberedListCounter: &numberedListCounter)
            lines.append(contentsOf: rendered)
        }

        return lines.joined(separator: "\n")
    }

    private static func renderBlock(_ block: DocumentBlock, numberedListCounter: inout Int) -> [String] {
        switch block.type {
        case .text:
            return [block.content, ""]

        case .heading1:
            return ["# \(block.content)", ""]

        case .heading2:
            return ["## \(block.content)", ""]

        case .heading3:
            return ["### \(block.content)", ""]

        case .bulletList:
            return ["- \(block.content)"]

        case .numberedList:
            numberedListCounter += 1
            return ["\(numberedListCounter). \(block.content)"]

        case .checkbox:
            let check = block.isChecked ? "x" : " "
            return ["- [\(check)] \(block.content)"]

        case .code:
            let lang = block.codeLanguage ?? ""
            return ["```\(lang)", block.content, "```", ""]

        case .quote:
            return ["> \(block.content)", ""]

        case .divider:
            return ["---", ""]

        case .calloutInfo:
            return ["> **Info:** \(block.content)", ""]

        case .calloutWarning:
            return ["> **Warning:** \(block.content)", ""]

        case .calloutSuccess:
            return ["> **Success:** \(block.content)", ""]

        case .calloutError:
            return ["> **Error:** \(block.content)", ""]

        case .image:
            if block.content.isEmpty {
                return ["*[Image]*", ""]
            }
            return ["*[Image: \(block.content)]*", ""]

        case .chart:
            let title = block.chartConfig?.title ?? "Chart"
            return ["*[Chart: \(title)]*", ""]
        }
    }
}

// MARK: - HTML Renderer

struct HTMLRenderer {

    /// Convert an array of DocumentBlocks to a complete HTML document string.
    static func render(blocks: [DocumentBlock], title: String? = nil, includeTitle: Bool = true, fontSize: CGFloat = 14) -> String {
        var bodyParts: [String] = []

        if includeTitle, let title, !title.isEmpty {
            bodyParts.append("    <h1>\(escapeHTML(title))</h1>")
        }

        var inList: String? = nil  // "ul", "ol"

        for block in blocks {
            let isListItem = block.type == .bulletList || block.type == .numberedList || block.type == .checkbox

            // Close list if needed
            if !isListItem, let listTag = inList {
                bodyParts.append("    </\(listTag)>")
                inList = nil
            }

            // Open list if needed
            if isListItem {
                let neededTag = block.type == .numberedList ? "ol" : "ul"
                if inList != neededTag {
                    if let listTag = inList {
                        bodyParts.append("    </\(listTag)>")
                    }
                    bodyParts.append("    <\(neededTag)>")
                    inList = neededTag
                }
            }

            bodyParts.append(contentsOf: renderBlockHTML(block))
        }

        // Close trailing list
        if let listTag = inList {
            bodyParts.append("    </\(listTag)>")
        }

        let body = bodyParts.joined(separator: "\n")
        let displayTitle = title ?? "Export"

        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>\(escapeHTML(displayTitle))</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: \(Int(fontSize))px;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 0 20px;
                    color: #1a1a1a;
                }
                h1 { font-size: 2em; margin-bottom: 0.5em; }
                h2 { font-size: 1.5em; margin-top: 1.5em; }
                h3 { font-size: 1.2em; margin-top: 1.2em; }
                pre { background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; }
                code { font-family: 'SF Mono', Menlo, monospace; font-size: 0.9em; }
                blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 16px; color: #555; }
                hr { border: none; border-top: 1px solid #e0e0e0; margin: 24px 0; }
                .callout { padding: 12px 16px; border-radius: 6px; margin: 8px 0; }
                .callout-info { background: #e8f4fd; border-left: 4px solid #2196F3; }
                .callout-warning { background: #fff8e1; border-left: 4px solid #FF9800; }
                .callout-success { background: #e8f5e9; border-left: 4px solid #4CAF50; }
                .callout-error { background: #fce4ec; border-left: 4px solid #f44336; }
                img { max-width: 100%; border-radius: 8px; }
            </style>
        </head>
        <body>
        \(body)
        </body>
        </html>
        """
    }

    private static func renderBlockHTML(_ block: DocumentBlock) -> [String] {
        let content = escapeHTML(block.content)

        switch block.type {
        case .text:
            return content.isEmpty ? ["    <br>"] : ["    <p>\(content)</p>"]

        case .heading1:
            return ["    <h1>\(content)</h1>"]

        case .heading2:
            return ["    <h2>\(content)</h2>"]

        case .heading3:
            return ["    <h3>\(content)</h3>"]

        case .bulletList:
            return ["      <li>\(content)</li>"]

        case .numberedList:
            return ["      <li>\(content)</li>"]

        case .checkbox:
            let checked = block.isChecked ? " checked disabled" : " disabled"
            return ["      <li><input type=\"checkbox\"\(checked)> \(content)</li>"]

        case .code:
            let lang = block.codeLanguage.map { " class=\"language-\($0)\"" } ?? ""
            return ["    <pre><code\(lang)>\(content)</code></pre>"]

        case .quote:
            return ["    <blockquote>\(content)</blockquote>"]

        case .divider:
            return ["    <hr>"]

        case .calloutInfo:
            return ["    <div class=\"callout callout-info\"><strong>Info:</strong> \(content)</div>"]

        case .calloutWarning:
            return ["    <div class=\"callout callout-warning\"><strong>Warning:</strong> \(content)</div>"]

        case .calloutSuccess:
            return ["    <div class=\"callout callout-success\"><strong>Success:</strong> \(content)</div>"]

        case .calloutError:
            return ["    <div class=\"callout callout-error\"><strong>Error:</strong> \(content)</div>"]

        case .image:
            if let imageData = block.imageData {
                let base64 = imageData.base64EncodedString()
                let caption = content.isEmpty ? "" : "<figcaption>\(content)</figcaption>"
                return ["    <figure><img src=\"data:image/png;base64,\(base64)\" alt=\"\(content)\">\(caption)</figure>"]
            }
            return content.isEmpty ? ["    <p><em>[Image]</em></p>"] : ["    <p><em>[Image: \(content)]</em></p>"]

        case .chart:
            let title = block.chartConfig?.title ?? "Chart"
            return ["    <div class=\"chart-placeholder\"><em>[Chart: \(escapeHTML(title))]</em></div>"]
        }
    }

    private static func escapeHTML(_ string: String) -> String {
        string
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
            .replacingOccurrences(of: "\"", with: "&quot;")
    }
}

// MARK: - CSV Renderer

struct CSVRenderer {

    /// Convert a SpreadsheetDocument to a CSV string.
    static func render(spreadsheet: SpreadsheetDocument, includeTitle: Bool = false) -> String {
        var lines: [String] = []

        if includeTitle {
            lines.append("# \(spreadsheet.title)")
        }

        // Find the actual data bounds
        var maxRow = 0
        var maxCol = 0

        for key in spreadsheet.cells.keys {
            if let addr = CellAddress.fromString(key) {
                maxRow = max(maxRow, addr.row)
                maxCol = max(maxCol, addr.column)
            }
        }

        // Generate rows
        for row in 0...maxRow {
            var cols: [String] = []
            for col in 0...maxCol {
                let addr = CellAddress(column: col, row: row)
                let cell = spreadsheet.cell(at: addr)
                cols.append(csvEscape(cell.rawValue))
            }
            lines.append(cols.joined(separator: ","))
        }

        return lines.joined(separator: "\n")
    }

    private static func csvEscape(_ value: String) -> String {
        if value.contains(",") || value.contains("\"") || value.contains("\n") {
            return "\"\(value.replacingOccurrences(of: "\"", with: "\"\""))\""
        }
        return value
    }
}
