//
//  WorkspaceTemplate.swift
//  MagnetarStudio
//
//  Template model for Notes, Docs, and Sheets.
//  Supports built-in and user-created templates with variable substitution.
//

import Foundation

// MARK: - Target Panel

enum TemplateTargetPanel: String, Codable, CaseIterable, Identifiable, Sendable {
    case note = "note"
    case doc = "doc"
    case sheet = "sheet"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .note: return "Note"
        case .doc: return "Document"
        case .sheet: return "Spreadsheet"
        }
    }

    var icon: String {
        switch self {
        case .note: return "note.text"
        case .doc: return "doc.text"
        case .sheet: return "tablecells"
        }
    }
}

// MARK: - Template Category

enum WorkspaceTemplateCategory: String, Codable, CaseIterable, Identifiable, Sendable {
    case productivity = "Productivity"
    case business = "Business"
    case personal = "Personal"
    case education = "Education"
    case finance = "Finance"
    case custom = "Custom"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .productivity: return "checkmark.circle"
        case .business: return "briefcase"
        case .personal: return "person"
        case .education: return "graduationcap"
        case .finance: return "dollarsign.circle"
        case .custom: return "star"
        }
    }
}

// MARK: - Template Variable

struct TemplateVariable: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var name: String
    var placeholder: String
    var type: VariableType
    var choices: [String]?

    init(
        id: UUID = UUID(),
        name: String,
        placeholder: String = "",
        type: VariableType = .text,
        choices: [String]? = nil
    ) {
        self.id = id
        self.name = name
        self.placeholder = placeholder.isEmpty ? name : placeholder
        self.type = type
        self.choices = choices
    }

    enum VariableType: String, Codable, CaseIterable {
        case text, number, date, choice
    }
}

// MARK: - Template Block

struct TemplateBlock: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var type: BlockType
    var content: String // May contain {{variableName}} placeholders

    init(id: UUID = UUID(), type: BlockType = .text, content: String = "") {
        self.id = id
        self.type = type
        self.content = content
    }
}

// MARK: - Template Cell (for sheets)

struct TemplateCell: Codable, Equatable, Sendable {
    var address: String  // "A1", "B2", etc.
    var value: String    // May contain {{variableName}} placeholders
    var isBold: Bool
    var isItalic: Bool

    init(address: String, value: String, isBold: Bool = false, isItalic: Bool = false) {
        self.address = address
        self.value = value
        self.isBold = isBold
        self.isItalic = isItalic
    }
}

// MARK: - Template Content

/// Sum type ensuring a template has either block content (notes/docs) or cell content (sheets), never both.
enum TemplateContent: Codable, Equatable, Sendable {
    case blocks([TemplateBlock])
    case cells([TemplateCell])
}

// MARK: - Workspace Template

struct WorkspaceTemplate: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var name: String
    var description: String
    var category: WorkspaceTemplateCategory
    var icon: String
    var targetPanel: TemplateTargetPanel
    var content: TemplateContent?
    var variables: [TemplateVariable]
    var isBuiltin: Bool
    var createdAt: Date
    var updatedAt: Date

    /// Convenience accessors for block-based content.
    var blocks: [TemplateBlock]? {
        if case .blocks(let b) = content { return b } else { return nil }
    }

    /// Convenience accessors for cell-based content.
    var cells: [TemplateCell]? {
        if case .cells(let c) = content { return c } else { return nil }
    }

    init(
        id: UUID = UUID(),
        name: String,
        description: String = "",
        category: WorkspaceTemplateCategory = .custom,
        icon: String = "doc.text",
        targetPanel: TemplateTargetPanel = .note,
        content: TemplateContent? = nil,
        variables: [TemplateVariable] = [],
        isBuiltin: Bool = false,
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.icon = icon
        self.targetPanel = targetPanel
        self.content = content
        self.variables = variables
        self.isBuiltin = isBuiltin
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    /// Fill variables in template content and return content string.
    func instantiate(variables: [String: String]) -> String {
        guard let content else { return "" }
        switch content {
        case .blocks(let blocks):
            return blocks.map { block in
                substituteVariables(in: block.content, values: variables)
            }.joined(separator: "\n")

        case .cells(let cells):
            let filled = cells.map { cell in
                TemplateCell(
                    address: cell.address,
                    value: substituteVariables(in: cell.value, values: variables),
                    isBold: cell.isBold,
                    isItalic: cell.isItalic
                )
            }
            let data = (try? JSONEncoder().encode(filled)) ?? Data()
            return String(data: data, encoding: .utf8) ?? ""
        }
    }

    private func substituteVariables(in text: String, values: [String: String]) -> String {
        var result = text
        for (key, value) in values {
            result = result.replacingOccurrences(of: "{{\(key)}}", with: value)
        }
        return result
    }
}
