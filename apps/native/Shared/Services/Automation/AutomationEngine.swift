//
//  AutomationEngine.swift
//  MagnetarStudio
//
//  Executes automation actions. Bridges to ExportService, WorkspaceAIService,
//  notification center, and other app services.
//

import Foundation
import UserNotifications
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AutomationEngine")

struct AutomationEngine {

    enum EngineError: Error, LocalizedError {
        case unsupportedAction(String)
        case exportFailed(String)
        case actionFailed(String)

        var errorDescription: String? {
            switch self {
            case .unsupportedAction(let msg): return "Unsupported action: \(msg)"
            case .exportFailed(let msg): return "Export failed: \(msg)"
            case .actionFailed(let msg): return "Action failed: \(msg)"
            }
        }
    }

    // MARK: - Execute Action

    @MainActor
    static func execute(action: AutomationAction, context: TriggerContext) async throws {
        logger.info("Executing action: \(action.displayName)")

        switch action {
        case .exportDocument(let format):
            try await executeExport(format: format, context: context)

        case .runAI(let prompt):
            try await executeAI(prompt: prompt, context: context)

        case .moveKanbanTask(let toColumn):
            try await executeMoveKanban(toColumn: toColumn, context: context)

        case .sendNotification(let title, let body):
            try await executeNotification(title: title, body: body, context: context)

        case .createNote(let title, let content):
            try await executeCreateNote(title: title, content: content, context: context)

        case .updateCell(let address, let value):
            try await executeUpdateCell(address: address, value: value, context: context)
        }
    }

    // MARK: - Action Implementations

    private static func executeExport(format: DocumentExportFormat, context: TriggerContext) async throws {
        // Export uses the ExportService from Phase 1
        guard let documentTitle = context.fields["documentTitle"] else {
            throw EngineError.exportFailed("No document context for export")
        }
        let content = context.fields["content"] ?? ""

        let options = ExportOptions(format: format, includeTitle: true)
        let exportContent = ExportContent.plainText(content, title: documentTitle)

        try await ExportService.shared.export(content: exportContent, options: options)
        logger.info("Auto-exported '\(documentTitle)' as \(format.rawValue)")
    }

    @MainActor
    private static func executeAI(prompt: String, context: TriggerContext) async throws {
        guard !prompt.isEmpty else {
            throw EngineError.actionFailed("AI prompt is empty")
        }

        // Substitute context fields into prompt
        var resolvedPrompt = prompt
        for (key, value) in context.fields {
            resolvedPrompt = resolvedPrompt.replacingOccurrences(of: "{{\(key)}}", with: value)
        }

        // STUB: AI execution — would call WorkspaceAIService with the resolved prompt.
        // The result could be stored or used in subsequent actions.
        logger.warning("STUB: AI prompt prepared but not executed — integration pending: \(resolvedPrompt.prefix(50))...")
    }

    @MainActor
    private static func executeMoveKanban(toColumn: String, context: TriggerContext) async throws {
        guard !toColumn.isEmpty else {
            throw EngineError.actionFailed("Target column not specified")
        }
        // STUB: Kanban integration — would call KanbanStore.shared.moveTask()
        logger.warning("STUB: Would move Kanban task to column '\(toColumn)' — integration pending")
    }

    private static func executeNotification(title: String, body: String, context: TriggerContext) async throws {
        // Substitute context fields
        var resolvedTitle = title
        var resolvedBody = body
        for (key, value) in context.fields {
            resolvedTitle = resolvedTitle.replacingOccurrences(of: "{{\(key)}}", with: value)
            resolvedBody = resolvedBody.replacingOccurrences(of: "{{\(key)}}", with: value)
        }

        let content = UNMutableNotificationContent()
        content.title = resolvedTitle
        content.body = resolvedBody
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil  // Fire immediately
        )

        try await UNUserNotificationCenter.current().add(request)
        logger.info("Sent notification: \(resolvedTitle)")
    }

    @MainActor
    private static func executeCreateNote(title: String, content: String, context: TriggerContext) async throws {
        var resolvedTitle = title
        var resolvedContent = content
        for (key, value) in context.fields {
            resolvedTitle = resolvedTitle.replacingOccurrences(of: "{{\(key)}}", with: value)
            resolvedContent = resolvedContent.replacingOccurrences(of: "{{\(key)}}", with: value)
        }

        // STUB: Note creation — would write to NotesPanel storage directory
        logger.warning("STUB: Would create note '\(resolvedTitle)' — integration pending")
    }

    @MainActor
    private static func executeUpdateCell(address: String, value: String, context: TriggerContext) async throws {
        guard let cellAddr = CellAddress.fromString(address) else {
            throw EngineError.actionFailed("Invalid cell address: \(address)")
        }

        var resolvedValue = value
        for (key, val) in context.fields {
            resolvedValue = resolvedValue.replacingOccurrences(of: "{{\(key)}}", with: val)
        }

        // STUB: Cell update — would write to SheetsPanel storage directory
        logger.warning("STUB: Would update cell \(cellAddr) to '\(resolvedValue)' — integration pending")
    }
}
