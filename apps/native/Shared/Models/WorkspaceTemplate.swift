//
//  WorkspaceTemplate.swift
//  MagnetarStudio
//
//  Template model for Notes, Docs, and Sheets.
//  Supports built-in and user-created templates with variable substitution.
//

import Foundation
import os

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

    enum VariableType: String, Codable, CaseIterable, Sendable {
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

    private enum CodingKeys: String, CodingKey {
        case blocks, cells
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let blocks = try container.decodeIfPresent([TemplateBlock].self, forKey: .blocks) {
            self = .blocks(blocks)
        } else if let cells = try container.decodeIfPresent([TemplateCell].self, forKey: .cells) {
            self = .cells(cells)
        } else {
            throw DecodingError.dataCorrupted(.init(
                codingPath: decoder.codingPath,
                debugDescription: "TemplateContent requires either 'blocks' or 'cells' key"
            ))
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .blocks(let blocks):
            try container.encode(blocks, forKey: .blocks)
        case .cells(let cells):
            try container.encode(cells, forKey: .cells)
        }
    }
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

    // MARK: - Codable (flat "blocks"/"cells" keys, not nested under "content")

    private enum CodingKeys: String, CodingKey {
        case id, name, description, category, icon, targetPanel
        case blocks, cells
        case variables, isBuiltin, createdAt, updatedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        description = try container.decodeIfPresent(String.self, forKey: .description) ?? ""
        category = try container.decode(WorkspaceTemplateCategory.self, forKey: .category)
        icon = try container.decode(String.self, forKey: .icon)
        targetPanel = try container.decode(TemplateTargetPanel.self, forKey: .targetPanel)
        variables = try container.decodeIfPresent([TemplateVariable].self, forKey: .variables) ?? []
        isBuiltin = try container.decodeIfPresent(Bool.self, forKey: .isBuiltin) ?? false
        createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt) ?? Date()
        updatedAt = try container.decodeIfPresent(Date.self, forKey: .updatedAt) ?? Date()

        // Read flat "blocks"/"cells" keys and wrap into TemplateContent sum type
        if let blocks = try container.decodeIfPresent([TemplateBlock].self, forKey: .blocks) {
            content = .blocks(blocks)
        } else if let cells = try container.decodeIfPresent([TemplateCell].self, forKey: .cells) {
            content = .cells(cells)
        } else {
            content = nil
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(description, forKey: .description)
        try container.encode(category, forKey: .category)
        try container.encode(icon, forKey: .icon)
        try container.encode(targetPanel, forKey: .targetPanel)
        try container.encode(variables, forKey: .variables)
        try container.encode(isBuiltin, forKey: .isBuiltin)
        try container.encode(createdAt, forKey: .createdAt)
        try container.encode(updatedAt, forKey: .updatedAt)

        // Write flat "blocks"/"cells" keys (matching JSON format)
        switch content {
        case .blocks(let blocks):
            try container.encode(blocks, forKey: .blocks)
        case .cells(let cells):
            try container.encode(cells, forKey: .cells)
        case nil:
            break
        }
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
            do {
                let data = try JSONEncoder().encode(filled)
                return String(data: data, encoding: .utf8) ?? ""
            } catch {
                Logger(subsystem: "com.magnetar.studio", category: "WorkspaceTemplate")
                    .error("Failed to encode template cells: \(error.localizedDescription)")
                return ""
            }
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
