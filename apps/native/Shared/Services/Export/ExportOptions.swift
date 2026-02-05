//
//  ExportOptions.swift
//  MagnetarStudio
//
//  Export format definitions and options for document/spreadsheet export.
//

import Foundation
import AppKit

// MARK: - Export Format

enum DocumentExportFormat: String, Codable, CaseIterable, Identifiable, Sendable {
    case pdf = "PDF"
    case markdown = "Markdown"
    case html = "HTML"
    case csv = "CSV"

    var id: String { rawValue }

    var fileExtension: String {
        switch self {
        case .pdf: return "pdf"
        case .markdown: return "md"
        case .html: return "html"
        case .csv: return "csv"
        }
    }

    var icon: String {
        switch self {
        case .pdf: return "doc.richtext"
        case .markdown: return "text.badge.checkmark"
        case .html: return "chevron.left.forwardslash.chevron.right"
        case .csv: return "tablecells"
        }
    }

    var contentType: String {
        switch self {
        case .pdf: return "application/pdf"
        case .markdown: return "text/markdown"
        case .html: return "text/html"
        case .csv: return "text/csv"
        }
    }
}

// MARK: - Export Content

/// Wraps different content types that can be exported.
enum ExportContent: Sendable {
    case blocks([DocumentBlock], title: String)
    case spreadsheet(SpreadsheetDocument)
    case plainText(String, title: String)
}

// MARK: - Page Size

enum ExportPageSize: String, Codable, CaseIterable, Identifiable, Sendable {
    case letter = "US Letter"
    case a4 = "A4"
    case legal = "Legal"

    var id: String { rawValue }

    var size: NSSize {
        switch self {
        case .letter: return NSSize(width: 612, height: 792)
        case .a4: return NSSize(width: 595, height: 842)
        case .legal: return NSSize(width: 612, height: 1008)
        }
    }
}

// MARK: - Export Options

struct ExportOptions: Codable, Sendable {
    var format: DocumentExportFormat = .pdf
    var includeTitle: Bool = true
    var pageSize: ExportPageSize = .letter
    var includeHeaderFooter: Bool = false
    var includePageNumbers: Bool = true
    var fontSize: CGFloat = 12
}

// MARK: - Export Error

enum ExportError: LocalizedError, Sendable {
    case unsupportedFormat(DocumentExportFormat, String)
    case renderingFailed(String)
    case saveFailed(String)

    var errorDescription: String? {
        switch self {
        case .unsupportedFormat(let format, let type):
            return "\(format.rawValue) export is not supported for \(type)"
        case .renderingFailed(let reason):
            return "Export rendering failed: \(reason)"
        case .saveFailed(let reason):
            return "Failed to save export: \(reason)"
        }
    }
}
