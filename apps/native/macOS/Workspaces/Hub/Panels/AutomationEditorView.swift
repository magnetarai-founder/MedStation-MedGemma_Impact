//
//  AutomationEditorView.swift
//  MagnetarStudio (macOS)
//
//  Visual rule builder: trigger picker → condition builder → action list.
//  Each action has its own configuration UI.
//

import SwiftUI

struct AutomationEditorView: View {
    @State private var rule: AutomationRule
    let onSave: (AutomationRule) -> Void
    let onCancel: () -> Void

    init(rule: AutomationRule? = nil, onSave: @escaping (AutomationRule) -> Void, onCancel: @escaping () -> Void) {
        self._rule = State(initialValue: rule ?? AutomationRule())
        self.onSave = onSave
        self.onCancel = onCancel
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text(rule.name == "New Rule" ? "New Automation Rule" : "Edit Rule")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
            }
            .padding(16)

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    basicInfoSection
                    Divider()
                    triggerSection
                    Divider()
                    conditionsSection
                    Divider()
                    actionsSection
                }
                .padding(16)
            }

            Divider()

            // Footer
            HStack {
                Spacer()
                Button("Cancel") { onCancel() }
                    .keyboardShortcut(.cancelAction)
                Button("Save Rule") {
                    rule.updatedAt = Date()
                    onSave(rule)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(rule.name.isEmpty || rule.actions.isEmpty)
            }
            .padding(16)
        }
        .frame(width: 520, height: 580)
    }

    // MARK: - Basic Info

    private var basicInfoSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("RULE INFO")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            TextField("Rule name", text: $rule.name)
                .textFieldStyle(.roundedBorder)

            TextField("Description (optional)", text: $rule.description)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12))
        }
    }

    // MARK: - Trigger

    private var triggerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("WHEN (TRIGGER)")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            ForEach(AutomationTrigger.allCases) { trigger in
                triggerOption(trigger)
            }

            if case .onSchedule = rule.trigger {
                HStack {
                    Text("Schedule:")
                        .font(.system(size: 11))
                    TextField("e.g., every 5m, hourly, daily 09:00", text: Binding(
                        get: {
                            if case .onSchedule(let cron) = rule.trigger { return cron }
                            return ""
                        },
                        set: { rule.trigger = .onSchedule(cron: $0) }
                    ))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12, design: .monospaced))
                }
                .padding(.leading, 28)
            }
        }
    }

    private func triggerOption(_ trigger: AutomationTrigger) -> some View {
        let isSelected = triggerMatches(rule.trigger, trigger)
        return Button {
            if case .onSchedule = trigger {
                rule.trigger = .onSchedule(cron: "")
            } else {
                rule.trigger = trigger
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
                    .font(.system(size: 14))

                Image(systemName: trigger.icon)
                    .font(.system(size: 12))
                    .frame(width: 16)

                Text(trigger.displayName)
                    .font(.system(size: 12))
                    .foregroundStyle(.primary)
            }
        }
        .buttonStyle(.plain)
    }

    private func triggerMatches(_ a: AutomationTrigger, _ b: AutomationTrigger) -> Bool {
        switch (a, b) {
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

    // MARK: - Conditions

    private var conditionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("IF (CONDITIONS)")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            Text("Optional — leave empty to always run")
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)

            ForEach(Array(rule.conditions.enumerated()), id: \.element.id) { index, _ in
                HStack(spacing: 6) {
                    TextField("Field", text: $rule.conditions[index].field)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 100)

                    Picker("", selection: $rule.conditions[index].operator) {
                        ForEach(ConditionOperator.allCases) { op in
                            Text(op.rawValue).tag(op)
                        }
                    }
                    .frame(width: 120)

                    TextField("Value", text: $rule.conditions[index].value)
                        .textFieldStyle(.roundedBorder)

                    Button {
                        rule.conditions.remove(at: index)
                    } label: {
                        Image(systemName: "minus.circle")
                            .foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                }
            }

            Button("Add Condition") {
                rule.conditions.append(AutomationCondition())
            }
            .controlSize(.small)
        }
    }

    // MARK: - Actions

    private var actionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("THEN (ACTIONS)")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            ForEach(Array(rule.actions.enumerated()), id: \.offset) { index, action in
                HStack(spacing: 8) {
                    Image(systemName: action.icon)
                        .font(.system(size: 12))
                        .foregroundStyle(Color.accentColor)
                        .frame(width: 16)

                    Text(action.displayName)
                        .font(.system(size: 12))

                    Spacer()

                    Button {
                        rule.actions.remove(at: index)
                    } label: {
                        Image(systemName: "minus.circle")
                            .foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                }
                .padding(8)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.surfaceTertiary)
                )
            }

            // Add action menu
            Menu {
                ForEach(AutomationAction.templates) { action in
                    Button {
                        rule.actions.append(action)
                    } label: {
                        Label(action.displayName, systemImage: action.icon)
                    }
                }
            } label: {
                Label("Add Action", systemImage: "plus")
                    .font(.system(size: 12))
            }
            .controlSize(.small)
        }
    }
}
