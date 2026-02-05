//
//  TemplateStore.swift
//  MagnetarStudio
//
//  Manages workspace templates — loads built-in from bundle, user templates from disk.
//  @MainActor @Observable singleton.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TemplateStore")

@MainActor
@Observable
final class TemplateStore {
    static let shared = TemplateStore()

    // MARK: - State

    var builtinTemplates: [WorkspaceTemplate] = []
    var userTemplates: [WorkspaceTemplate] = []
    var isLoading = true

    var allTemplates: [WorkspaceTemplate] {
        builtinTemplates + userTemplates
    }

    func templates(for panel: TemplateTargetPanel) -> [WorkspaceTemplate] {
        allTemplates.filter { $0.targetPanel == panel }
    }

    func templates(in category: WorkspaceTemplateCategory) -> [WorkspaceTemplate] {
        allTemplates.filter { $0.category == category }
    }

    private init() {}

    // MARK: - Loading

    func loadAll() async {
        isLoading = true
        defer { isLoading = false }

        loadBuiltinTemplates()
        await loadUserTemplates()

        logger.debug("[Templates] Loaded \(self.builtinTemplates.count) built-in, \(self.userTemplates.count) user templates")
    }

    private func loadBuiltinTemplates() {
        var templates: [WorkspaceTemplate] = []
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        for resourceName in ["notes_templates", "docs_templates", "sheets_templates"] {
            guard let url = Bundle.main.url(forResource: resourceName, withExtension: "json") else {
                logger.warning("[Templates] Could not find \(resourceName).json in bundle")
                continue
            }
            do {
                let data = try Data(contentsOf: url)
                let loaded = try decoder.decode([WorkspaceTemplate].self, from: data)
                templates.append(contentsOf: loaded)
            } catch {
                logger.warning("[Templates] Failed to decode \(resourceName).json: \(error.localizedDescription)")
            }
        }

        builtinTemplates = templates
    }

    private func loadUserTemplates() async {
        let dir = Self.userTemplatesDir
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter({ $0.pathExtension == "json" })
        } catch {
            logger.error("Failed to list user templates directory: \(error.localizedDescription)")
            return
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        var loaded: [WorkspaceTemplate] = []

        for file in files {
            // TemplateStore uses iso8601 date decoding — can't use PersistenceHelpers.load directly
            do {
                let data = try Data(contentsOf: file)
                let template = try decoder.decode(WorkspaceTemplate.self, from: data)
                loaded.append(template)
            } catch {
                logger.error("Failed to load template from \(file.lastPathComponent): \(error.localizedDescription)")
            }
        }

        userTemplates = loaded.sorted { $0.updatedAt > $1.updatedAt }
    }

    // MARK: - CRUD

    func save(template: WorkspaceTemplate) {
        if let index = userTemplates.firstIndex(where: { $0.id == template.id }) {
            userTemplates[index] = template
        } else {
            userTemplates.insert(template, at: 0)
        }
        saveToDisk(template)
    }

    func delete(template: WorkspaceTemplate) {
        guard !template.isBuiltin else { return }
        userTemplates.removeAll { $0.id == template.id }
        deleteFromDisk(template)
    }

    // MARK: - Instantiation

    /// Instantiate a template with given variable values.
    /// Returns the filled content string (for notes/docs) or JSON cells (for sheets).
    func instantiate(template: WorkspaceTemplate, variables: [String: String]) -> String {
        template.instantiate(variables: variables)
    }

    /// Instantiate a template as a new WorkspaceNote.
    func instantiateAsNote(template: WorkspaceTemplate, title: String, variables: [String: String]) -> WorkspaceNote {
        let content = template.instantiate(variables: variables)
        return WorkspaceNote(
            id: UUID(),
            title: title.isEmpty ? template.name : title,
            content: content,
            createdAt: Date(),
            updatedAt: Date(),
            isPinned: false
        )
    }

    /// Instantiate a template as a new SpreadsheetDocument.
    func instantiateAsSpreadsheet(template: WorkspaceTemplate, title: String, variables: [String: String]) -> SpreadsheetDocument {
        var doc = SpreadsheetDocument(title: title.isEmpty ? template.name : title)

        if let cells = template.cells {
            for templateCell in cells {
                let value = substituteVariables(in: templateCell.value, values: variables)
                if let addr = CellAddress.fromString(templateCell.address) {
                    var cell = SpreadsheetCell(rawValue: value)
                    cell.isBold = templateCell.isBold
                    cell.isItalic = templateCell.isItalic
                    doc.cells[addr.description] = cell
                }
            }
        }

        return doc
    }

    private func substituteVariables(in text: String, values: [String: String]) -> String {
        var result = text
        for (key, value) in values {
            result = result.replacingOccurrences(of: "{{\(key)}}", with: value)
        }
        return result
    }

    // MARK: - Persistence

    private static var userTemplatesDir: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio/templates", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "templates storage")
        return dir
    }

    private func saveToDisk(_ template: WorkspaceTemplate) {
        let file = Self.userTemplatesDir.appendingPathComponent("\(template.id.uuidString).json")
        // TemplateStore uses iso8601 date encoding, so we use a custom encoder
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(template)
            try data.write(to: file, options: .atomic)
        } catch {
            Logger(subsystem: "com.magnetar.studio", category: "Persistence")
                .error("Failed to save template '\(template.name)': \(error.localizedDescription)")
        }
    }

    private func deleteFromDisk(_ template: WorkspaceTemplate) {
        let file = Self.userTemplatesDir.appendingPathComponent("\(template.id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "template '\(template.name)'")
    }
}
