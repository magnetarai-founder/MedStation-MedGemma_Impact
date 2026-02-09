//
//  AutomationListView.swift
//  MagnetarStudio (macOS)
//
//  List of all automation rules with enable/disable toggles.
//  Shows last run time, run count, error status. CRUD actions.
//

import SwiftUI

struct AutomationListView: View {
    @State private var automationStore = AutomationStore.shared
    @State private var showEditor = false
    @State private var editingRule: AutomationRule?
    @State private var showLog = false
    @State private var searchText = ""
    @FocusState private var isSearchFocused: Bool

    private var filteredRules: [AutomationRule] {
        if searchText.isEmpty { return automationStore.rules }
        return automationStore.rules.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            $0.description.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar

            Divider()

            // Rules list
            if automationStore.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredRules.isEmpty {
                emptyState
            } else {
                rulesList
            }
        }
        .task {
            if automationStore.isLoading {
                await automationStore.loadAll()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .focusPanelSearch)) { _ in
            isSearchFocused = true
        }
        .sheet(isPresented: $showEditor) {
            AutomationEditorView(
                rule: nil,
                onSave: { rule in
                    automationStore.createRule(rule)
                    showEditor = false
                },
                onCancel: { showEditor = false }
            )
        }
        .sheet(item: $editingRule) { rule in
            AutomationEditorView(
                rule: rule,
                onSave: { updated in
                    automationStore.updateRule(updated)
                    editingRule = nil
                },
                onCancel: { editingRule = nil }
            )
        }
        .sheet(isPresented: $showLog) {
            AutomationLogView(onDismiss: { showLog = false })
        }
        .alert("Automation Error", isPresented: Binding(
            get: { automationStore.lastExecutionError != nil },
            set: { if !$0 { automationStore.lastExecutionError = nil } }
        )) {
            Button("OK") { automationStore.lastExecutionError = nil }
        } message: {
            Text(automationStore.lastExecutionError ?? "Unknown error")
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 10) {
            Image(systemName: "gearshape.2")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)

            Text("Automations")
                .font(.system(size: 14, weight: .semibold))

            Text("(\(automationStore.enabledRules.count) active)")
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)

            Spacer()

            // Search
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                TextField("Search...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .frame(width: 120)
                    .focused($isSearchFocused)
                if !searchText.isEmpty {
                    Button { searchText = "" } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear search")
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.gray.opacity(0.1))
            )

            Button {
                showLog = true
            } label: {
                Image(systemName: "list.bullet.rectangle")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .help("Execution Log")

            Button {
                showEditor = true
            } label: {
                Image(systemName: "plus")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .help("New Rule")
        }
        .padding(.horizontal, 16)
        .frame(height: HubLayout.headerHeight)
    }

    // MARK: - Rules List

    private var rulesList: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(filteredRules) { rule in
                    ruleRow(rule)
                }
            }
            .padding(16)
        }
    }

    private func ruleRow(_ rule: AutomationRule) -> some View {
        HStack(spacing: 12) {
            // Enable toggle
            Toggle("", isOn: Binding(
                get: { rule.isEnabled },
                set: { _ in automationStore.toggleRule(rule) }
            ))
            .labelsHidden()
            .toggleStyle(.switch)
            .controlSize(.small)

            // Icon
            Image(systemName: rule.trigger.icon)
                .font(.system(size: 14))
                .foregroundStyle(rule.isEnabled ? Color.accentColor : Color.secondary)
                .frame(width: 20)

            // Info
            VStack(alignment: .leading, spacing: 2) {
                Text(rule.name)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(rule.isEnabled ? .primary : .secondary)

                HStack(spacing: 8) {
                    Text(rule.trigger.displayName)
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)

                    if !rule.actions.isEmpty {
                        Text("→ \(rule.actions.count) actions")
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }

                    if let lastRun = rule.lastRunAt {
                        Text("Last: \(lastRun.formatted(.relative(presentation: .named)))")
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                }
            }

            Spacer()

            // Run count
            if rule.runCount > 0 {
                Text("\(rule.runCount)×")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.tertiary)
            }

            // Manual trigger
            if rule.isEnabled {
                Button {
                    AutomationTriggerService.shared.manualTrigger(for: rule)
                } label: {
                    Image(systemName: "play.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(.green)
                }
                .buttonStyle(.plain)
                .help("Run Now")
            }

            // Edit
            Button {
                editingRule = rule
            } label: {
                Image(systemName: "pencil")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .help("Edit Rule")

            // Delete
            Button {
                automationStore.deleteRule(rule)
            } label: {
                Image(systemName: "trash")
                    .font(.system(size: 11))
                    .foregroundStyle(.red.opacity(0.6))
            }
            .buttonStyle(.plain)
            .help("Delete Rule")
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color.surfaceTertiary)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.gray.opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "gearshape.2")
                .font(.system(size: 40))
                .foregroundStyle(.tertiary)
            Text("No automation rules yet")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
            Text("Create rules to automate repetitive tasks")
                .font(.system(size: 12))
                .foregroundStyle(.tertiary)
            Button("Create Rule") {
                showEditor = true
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
