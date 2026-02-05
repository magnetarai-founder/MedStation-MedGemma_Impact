//
//  AutomationTriggerService.swift
//  MagnetarStudio
//
//  Listens for events across the app and routes them to AutomationStore.evaluate().
//  Debounces rapid-fire triggers (cell changes).
//

import Foundation
import Combine
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AutomationTrigger")

@MainActor @Observable
final class AutomationTriggerService {
    static let shared = AutomationTriggerService()

    private var debounceTimers: [String: Task<Void, Never>] = [:]
    private let debounceInterval: TimeInterval = 0.5

    private init() {}

    // MARK: - Fire Triggers

    /// Fire a document save trigger.
    func documentSaved(title: String, content: String) {
        let context = TriggerContext(
            trigger: .onDocumentSave,
            fields: [
                "documentTitle": title,
                "content": content
            ]
        )
        fire(context, debounceKey: "docSave-\(title)")
    }

    /// Fire a recording stop trigger.
    func recordingStopped(title: String, transcript: String) {
        let context = TriggerContext(
            trigger: .onRecordingStop,
            fields: [
                "recordingTitle": title,
                "transcript": transcript
            ]
        )
        fire(context, debounceKey: nil)  // No debounce for recordings
    }

    /// Fire a sheet cell change trigger.
    func sheetCellChanged(sheetTitle: String, address: String, oldValue: String, newValue: String) {
        let context = TriggerContext(
            trigger: .onSheetCellChange,
            fields: [
                "sheetTitle": sheetTitle,
                "cellAddress": address,
                "oldValue": oldValue,
                "newValue": newValue
            ]
        )
        fire(context, debounceKey: "cellChange-\(sheetTitle)")
    }

    /// Fire a kanban status change trigger.
    func kanbanStatusChanged(taskTitle: String, fromColumn: String, toColumn: String) {
        let context = TriggerContext(
            trigger: .onKanbanStatusChange,
            fields: [
                "taskTitle": taskTitle,
                "fromColumn": fromColumn,
                "toColumn": toColumn
            ]
        )
        fire(context, debounceKey: nil)
    }

    /// Fire a manual trigger for a specific rule.
    func manualTrigger(for rule: AutomationRule) {
        let context = TriggerContext(trigger: .manual)
        Task {
            await AutomationStore.shared.evaluate(context: context)
        }
    }

    // MARK: - Internal

    private func fire(_ context: TriggerContext, debounceKey: String?) {
        guard FeatureFlags.shared.automations else { return }

        if let key = debounceKey {
            debounceTimers[key]?.cancel()
            debounceTimers[key] = Task {
                try? await Task.sleep(for: .seconds(debounceInterval))
                guard !Task.isCancelled else { return }
                await AutomationStore.shared.evaluate(context: context)
            }
        } else {
            Task {
                await AutomationStore.shared.evaluate(context: context)
            }
        }

        logger.debug("Trigger fired: \(context.trigger.displayName)")
    }
}
