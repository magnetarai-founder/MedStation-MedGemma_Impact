//
//  AutomationStore.swift
//  MagnetarStudio
//
//  @MainActor @Observable singleton for automation rule CRUD + evaluation.
//  Persists rules to ~/Library/Application Support/MagnetarStudio/automations/
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AutomationStore")

@MainActor @Observable
final class AutomationStore {
    static let shared = AutomationStore()

    var rules: [AutomationRule] = []
    var logEntries: [AutomationLogEntry] = []
    var isLoading = true

    private init() {}

    // MARK: - Persistence

    private static var rulesDir: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio/automations", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "automations storage")
        return dir
    }

    private static var logFile: URL {
        rulesDir.appendingPathComponent("execution_log.json")
    }

    func loadAll() async {
        defer { isLoading = false }
        await loadRules()
        loadLog()
    }

    private func loadRules() async {
        let dir = Self.rulesDir
        guard let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
            .filter({ $0.pathExtension == "json" && $0.lastPathComponent != "execution_log.json" }) else { return }

        var loaded: [AutomationRule] = []
        for file in files {
            if let rule = PersistenceHelpers.load(AutomationRule.self, from: file, label: "automation rule") {
                loaded.append(rule)
            }
        }
        rules = loaded.sorted { $0.updatedAt > $1.updatedAt }
        logger.info("Loaded \(loaded.count) automation rules")
    }

    private func loadLog() {
        guard let entries = PersistenceHelpers.load([AutomationLogEntry].self, from: Self.logFile, label: "automation log") else { return }
        logEntries = Array(entries.suffix(500))
    }

    // MARK: - CRUD

    func createRule(_ rule: AutomationRule) {
        rules.insert(rule, at: 0)
        saveRule(rule)
        logger.info("Created automation rule: \(rule.name)")
    }

    func updateRule(_ rule: AutomationRule) {
        if let index = rules.firstIndex(where: { $0.id == rule.id }) {
            var updated = rule
            updated.updatedAt = Date()
            rules[index] = updated
            saveRule(updated)
        }
    }

    func deleteRule(_ rule: AutomationRule) {
        rules.removeAll { $0.id == rule.id }
        let file = Self.rulesDir.appendingPathComponent("\(rule.id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "automation rule '\(rule.name)'")
        logger.info("Deleted automation rule: \(rule.name)")
    }

    func toggleRule(_ rule: AutomationRule) {
        if let index = rules.firstIndex(where: { $0.id == rule.id }) {
            rules[index].isEnabled.toggle()
            rules[index].updatedAt = Date()
            saveRule(rules[index])
        }
    }

    private func saveRule(_ rule: AutomationRule) {
        let file = Self.rulesDir.appendingPathComponent("\(rule.id.uuidString).json")
        PersistenceHelpers.save(rule, to: file, label: "automation rule '\(rule.name)'")
    }

    // MARK: - Evaluation

    /// Evaluate all enabled rules against a trigger context.
    func evaluate(context: TriggerContext) async {
        let matchingRules = rules.filter { $0.isEnabled && triggersMatch($0.trigger, context.trigger) }
        guard !matchingRules.isEmpty else { return }

        logger.info("Evaluating \(matchingRules.count) rules for trigger: \(context.trigger.displayName)")

        for rule in matchingRules {
            await executeRule(rule, context: context)
        }
    }

    private func triggersMatch(_ ruleTrigger: AutomationTrigger, _ eventTrigger: AutomationTrigger) -> Bool {
        switch (ruleTrigger, eventTrigger) {
        case (.onDocumentSave, .onDocumentSave),
             (.onRecordingStop, .onRecordingStop),
             (.onSheetCellChange, .onSheetCellChange),
             (.onKanbanStatusChange, .onKanbanStatusChange),
             (.manual, .manual):
            return true
        case (.onSchedule, .onSchedule):
            return true
        default:
            return false
        }
    }

    private func executeRule(_ rule: AutomationRule, context: TriggerContext) async {
        let start = Date()

        // Check conditions
        let conditionsMet = rule.conditions.allSatisfy { condition in
            let fieldValue = context.fields[condition.field] ?? ""
            return condition.operator.evaluate(fieldValue: fieldValue, conditionValue: condition.value)
        }

        guard conditionsMet else {
            let entry = AutomationLogEntry(
                ruleId: rule.id,
                ruleName: rule.name,
                trigger: context.trigger,
                status: .skipped,
                message: "Conditions not met",
                duration: Date().timeIntervalSince(start)
            )
            appendLogEntry(entry)
            return
        }

        // Execute actions
        do {
            for action in rule.actions {
                try await AutomationEngine.execute(action: action, context: context)
            }

            // Update rule
            if let index = rules.firstIndex(where: { $0.id == rule.id }) {
                rules[index].lastRunAt = Date()
                rules[index].runCount += 1
                saveRule(rules[index])
            }

            let entry = AutomationLogEntry(
                ruleId: rule.id,
                ruleName: rule.name,
                trigger: context.trigger,
                status: .success,
                message: "\(rule.actions.count) actions completed",
                duration: Date().timeIntervalSince(start)
            )
            appendLogEntry(entry)
            logger.info("Rule '\(rule.name)' executed successfully")

        } catch {
            let entry = AutomationLogEntry(
                ruleId: rule.id,
                ruleName: rule.name,
                trigger: context.trigger,
                status: .failure,
                message: error.localizedDescription,
                duration: Date().timeIntervalSince(start)
            )
            appendLogEntry(entry)
            logger.error("Rule '\(rule.name)' failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Log Management

    private func appendLogEntry(_ entry: AutomationLogEntry) {
        logEntries.insert(entry, at: 0)
        if logEntries.count > 500 {
            logEntries = Array(logEntries.prefix(500))
        }
        saveLog()
    }

    private func saveLog() {
        PersistenceHelpers.save(logEntries, to: Self.logFile, label: "automation log")
    }

    func clearLog() {
        logEntries.removeAll()
        saveLog()
    }

    // MARK: - Convenience

    var enabledRules: [AutomationRule] {
        rules.filter(\.isEnabled)
    }

    func rules(for trigger: AutomationTrigger) -> [AutomationRule] {
        rules.filter { triggersMatch($0.trigger, trigger) }
    }
}
