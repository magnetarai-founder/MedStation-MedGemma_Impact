//
//  AutomationLogView.swift
//  MagnetarStudio (macOS)
//
//  Execution history table: timestamp, rule name, trigger, result, duration.
//  Filter by rule, status, date range.
//

import SwiftUI

struct AutomationLogView: View {
    let onDismiss: () -> Void

    @State private var automationStore = AutomationStore.shared
    @State private var filterStatus: ExecutionStatus?
    @State private var searchText = ""

    private var filteredEntries: [AutomationLogEntry] {
        var entries = automationStore.logEntries
        if let status = filterStatus {
            entries = entries.filter { $0.status == status }
        }
        if !searchText.isEmpty {
            entries = entries.filter {
                $0.ruleName.localizedCaseInsensitiveContains(searchText) ||
                $0.message.localizedCaseInsensitiveContains(searchText)
            }
        }
        return entries
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "list.bullet.rectangle")
                    .font(.system(size: 14))
                    .foregroundStyle(Color.accentColor)
                Text("Execution Log")
                    .font(.system(size: 14, weight: .semibold))

                Spacer()

                // Filter chips
                filterChip(nil, label: "All")
                filterChip(.success, label: "Success")
                filterChip(.failure, label: "Failed")
                filterChip(.skipped, label: "Skipped")

                Divider().frame(height: 16)

                Button("Clear") {
                    automationStore.clearLog()
                }
                .controlSize(.small)

                Button { onDismiss() } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(16)

            Divider()

            // Search
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                TextField("Search log...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            Divider()

            // Log entries
            if filteredEntries.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "clock")
                        .font(.system(size: 24))
                        .foregroundStyle(.tertiary)
                    Text("No log entries")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 4) {
                        ForEach(filteredEntries) { entry in
                            logEntryRow(entry)
                        }
                    }
                    .padding(12)
                }
            }
        }
        .frame(width: 600, height: 450)
    }

    // MARK: - Log Entry Row

    private func logEntryRow(_ entry: AutomationLogEntry) -> some View {
        HStack(spacing: 10) {
            // Status indicator
            Circle()
                .fill(statusColor(entry.status))
                .frame(width: 8, height: 8)

            // Rule name
            Text(entry.ruleName)
                .font(.system(size: 12, weight: .medium))
                .frame(width: 120, alignment: .leading)
                .lineLimit(1)

            // Trigger
            Text(entry.trigger.displayName)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .frame(width: 100, alignment: .leading)

            // Message
            Text(entry.message)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .lineLimit(1)

            Spacer()

            // Duration
            Text(String(format: "%.1fs", entry.duration))
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.tertiary)
                .frame(width: 40, alignment: .trailing)

            // Timestamp
            Text(entry.timestamp.formatted(.dateTime.hour().minute().second()))
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
                .frame(width: 60, alignment: .trailing)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(entry.status == .failure ? Color.red.opacity(0.05) : Color.clear)
        )
    }

    // MARK: - Helpers

    private func filterChip(_ status: ExecutionStatus?, label: String) -> some View {
        let isSelected = filterStatus == status
        return Button {
            filterStatus = status
        } label: {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(isSelected ? .white : .secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(isSelected ? Color.accentColor : Color.gray.opacity(0.1))
                )
        }
        .buttonStyle(.plain)
    }

    private func statusColor(_ status: ExecutionStatus) -> Color {
        switch status {
        case .success: return .green
        case .failure: return .red
        case .skipped: return .orange
        }
    }
}
