//
//  AutomationRule.swift
//  MagnetarStudio
//
//  Rule-based automation: triggers → conditions → actions.
//  Codable for persistence, Identifiable for SwiftUI lists.
//

import Foundation

// MARK: - Automation Rule

struct AutomationRule: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var name: String
    var description: String
    var trigger: AutomationTrigger
    var conditions: [AutomationCondition]
    var actions: [AutomationAction]
    var isEnabled: Bool
    var lastRunAt: Date?
    var runCount: Int
    var createdAt: Date
    var updatedAt: Date

    init(
        id: UUID = UUID(),
        name: String = "New Rule",
        description: String = "",
        trigger: AutomationTrigger = .manual,
        conditions: [AutomationCondition] = [],
        actions: [AutomationAction] = [],
        isEnabled: Bool = true,
        lastRunAt: Date? = nil,
        runCount: Int = 0,
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.name = name
        self.description = description
        self.trigger = trigger
        self.conditions = conditions
        self.actions = actions
        self.isEnabled = isEnabled
        self.lastRunAt = lastRunAt
        self.runCount = runCount
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - Trigger

enum AutomationTrigger: Codable, Equatable, CaseIterable, Identifiable, Sendable {
    case onDocumentSave
    case onRecordingStop
    case onSheetCellChange
    case onKanbanStatusChange
    case onSchedule(cron: String)
    case manual

    var id: String { displayName }

    var displayName: String {
        switch self {
        case .onDocumentSave: return "Document Saved"
        case .onRecordingStop: return "Recording Stopped"
        case .onSheetCellChange: return "Sheet Cell Changed"
        case .onKanbanStatusChange: return "Kanban Status Changed"
        case .onSchedule: return "On Schedule"
        case .manual: return "Manual"
        }
    }

    var icon: String {
        switch self {
        case .onDocumentSave: return "doc.badge.arrow.up"
        case .onRecordingStop: return "waveform.badge.mic"
        case .onSheetCellChange: return "tablecells.badge.ellipsis"
        case .onKanbanStatusChange: return "rectangle.3.group"
        case .onSchedule: return "clock"
        case .manual: return "play.circle"
        }
    }

    // CaseIterable conformance (excluding associated values)
    static var allCases: [AutomationTrigger] {
        [.onDocumentSave, .onRecordingStop, .onSheetCellChange, .onKanbanStatusChange, .onSchedule(cron: "every 5m"), .manual]
    }

    /// Trigger types for UI pickers — use this instead of allCases
    static var pickerCases: [AutomationTrigger] {
        [.onDocumentSave, .onRecordingStop, .onSheetCellChange, .onKanbanStatusChange, .onSchedule(cron: "every 5m"), .manual]
    }
}

// MARK: - Condition

struct AutomationCondition: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var field: String            // e.g., "title", "cellValue", "status"
    var `operator`: ConditionOperator
    var value: String

    init(id: UUID = UUID(), field: String = "", operator: ConditionOperator = .equals, value: String = "") {
        self.id = id
        self.field = field
        self.operator = `operator`
        self.value = value
    }
}

enum ConditionOperator: String, Codable, CaseIterable, Identifiable, Sendable {
    case equals = "equals"
    case notEquals = "not equals"
    case contains = "contains"
    case notContains = "not contains"
    case greaterThan = "greater than"
    case lessThan = "less than"
    case isEmpty = "is empty"
    case isNotEmpty = "is not empty"

    var id: String { rawValue }

    func evaluate(fieldValue: String, conditionValue: String) -> Bool {
        switch self {
        case .equals:
            return fieldValue == conditionValue
        case .notEquals:
            return fieldValue != conditionValue
        case .contains:
            return fieldValue.localizedCaseInsensitiveContains(conditionValue)
        case .notContains:
            return !fieldValue.localizedCaseInsensitiveContains(conditionValue)
        case .greaterThan:
            return (Double(fieldValue) ?? 0) > (Double(conditionValue) ?? 0)
        case .lessThan:
            return (Double(fieldValue) ?? 0) < (Double(conditionValue) ?? 0)
        case .isEmpty:
            return fieldValue.isEmpty
        case .isNotEmpty:
            return !fieldValue.isEmpty
        }
    }
}

// MARK: - Action

enum AutomationAction: Codable, Identifiable, Equatable, Sendable {
    case exportDocument(format: DocumentExportFormat)
    case runAI(prompt: String)
    case moveKanbanTask(toColumn: String)
    case sendNotification(title: String, body: String)
    case createNote(title: String, content: String)
    case updateCell(address: String, value: String)

    var id: String {
        switch self {
        case .exportDocument(let f): return "export-\(f.rawValue)"
        case .runAI(let p): return "ai-\(p.hashValue)"
        case .moveKanbanTask(let c): return "kanban-\(c)"
        case .sendNotification(let t, let b): return "notify-\(t.hashValue)-\(b.hashValue)"
        case .createNote(let t, let c): return "note-\(t.hashValue)-\(c.hashValue)"
        case .updateCell(let a, let v): return "cell-\(a)-\(v.hashValue)"
        }
    }

    var displayName: String {
        switch self {
        case .exportDocument(let format): return "Export as \(format.rawValue.uppercased())"
        case .runAI: return "Run AI Prompt"
        case .moveKanbanTask(let col): return "Move to \(col)"
        case .sendNotification: return "Send Notification"
        case .createNote: return "Create Note"
        case .updateCell(let addr, _): return "Update Cell \(addr)"
        }
    }

    var icon: String {
        switch self {
        case .exportDocument: return "arrow.up.doc"
        case .runAI: return "sparkles"
        case .moveKanbanTask: return "rectangle.3.group"
        case .sendNotification: return "bell"
        case .createNote: return "note.text.badge.plus"
        case .updateCell: return "tablecells"
        }
    }

    static var templates: [AutomationAction] {
        [
            .exportDocument(format: .pdf),
            .runAI(prompt: ""),
            .moveKanbanTask(toColumn: ""),
            .sendNotification(title: "", body: ""),
            .createNote(title: "", content: ""),
            .updateCell(address: "", value: "")
        ]
    }
}

// MARK: - Execution Log

struct AutomationLogEntry: Codable, Identifiable, Sendable {
    let id: UUID
    let ruleId: UUID
    let ruleName: String
    let trigger: AutomationTrigger
    let status: ExecutionStatus
    let message: String
    let duration: TimeInterval
    let timestamp: Date

    init(
        id: UUID = UUID(),
        ruleId: UUID,
        ruleName: String,
        trigger: AutomationTrigger,
        status: ExecutionStatus,
        message: String = "",
        duration: TimeInterval = 0,
        timestamp: Date = Date()
    ) {
        self.id = id
        self.ruleId = ruleId
        self.ruleName = ruleName
        self.trigger = trigger
        self.status = status
        self.message = message
        self.duration = duration
        self.timestamp = timestamp
    }
}

enum ExecutionStatus: String, Codable, Sendable {
    case success
    case failure
    case skipped
}

// MARK: - Trigger Context

struct TriggerContext: Sendable {
    let trigger: AutomationTrigger
    let fields: [String: String]  // field name → value for condition evaluation

    init(trigger: AutomationTrigger, fields: [String: String] = [:]) {
        self.trigger = trigger
        self.fields = fields
    }
}
