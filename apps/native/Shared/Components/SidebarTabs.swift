//
//  SidebarTabs.swift
//  MagnetarStudio
//
//  Two-tab sidebar component: Columns | Logs
//  - Active tab has primary color with 2px bottom border
//  - Inactive tabs are gray with hover effect
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SidebarTabs")

struct SidebarTabs: View {
    @State private var selectedTab: SidebarTab = .columns
    @State private var columns: [SidebarColumnInfo] = []
    @State private var logs: [LogEntry] = []

    var body: some View {
        VStack(spacing: 0) {
            // Tab header
            HStack(spacing: 0) {
                Spacer()

                TabButton(
                    title: "Columns",
                    isSelected: selectedTab == .columns,
                    action: { selectedTab = .columns }
                )

                TabButton(
                    title: "Logs",
                    isSelected: selectedTab == .logs,
                    action: { selectedTab = .logs }
                )

                Spacer()
            }
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Tab content
            Group {
                switch selectedTab {
                case .columns:
                    ColumnInspector(columns: columns)
                case .logs:
                    LogViewer(logs: logs)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

// MARK: - Tab Button

struct TabButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(isSelected ? .magnetarPrimary : (isHovered ? .primary : .secondary))
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .overlay(
                    Rectangle()
                        .fill(isSelected ? Color.magnetarPrimary : Color.clear)
                        .frame(height: 2),
                    alignment: .bottom
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Column Inspector

struct ColumnInspector: View {
    let columns: [SidebarColumnInfo]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if columns.isEmpty {
                // Empty state
                VStack(spacing: 12) {
                    Image(systemName: "cylinder")
                        .font(.system(size: 32))
                        .foregroundColor(.secondary)

                    Text("No file loaded")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                // Header
                HStack {
                    Text("Columns (\(columns.count))")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(.primary)

                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)
                .padding(.bottom, 8)

                // Column list
                ScrollView {
                    VStack(spacing: 0) {
                        ForEach(columns) { column in
                            ColumnRow(column: column)
                        }
                    }
                    .background(Color(.controlBackgroundColor))
                    .cornerRadius(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                }
                .padding(.horizontal, 16)
            }
        }
    }
}

struct ColumnRow: View {
    let column: SidebarColumnInfo
    @State private var isHovered = false

    var body: some View {
        HStack {
            Text(column.name)
                .font(.system(size: 13))
                .foregroundColor(.primary)

            Spacer()

            if isHovered && column.isClickable {
                Image(systemName: "plus.circle")
                    .font(.system(size: 16))
                    .foregroundColor(.magnetarPrimary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isHovered ? Color.gray.opacity(0.1) : Color.clear)
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.2))
                .frame(height: 1),
            alignment: .bottom
        )
        .onHover { hovering in
            if column.isClickable {
                isHovered = hovering
            }
        }
        .onTapGesture {
            if column.isClickable {
                // Insert column into query
                logger.debug("Insert column: \(column.name)")
            }
        }
    }
}

// MARK: - Log Viewer

struct LogViewer: View {
    let logs: [LogEntry]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if logs.isEmpty {
                // Empty state
                VStack(spacing: 12) {
                    Image(systemName: "doc.text")
                        .font(.system(size: 32))
                        .foregroundColor(.secondary)

                    Text("No logs yet")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(logs) { log in
                            LogRow(log: log)
                        }
                    }
                    .padding(12)
                }
            }
        }
    }
}

struct LogRow: View {
    let log: LogEntry

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(log.timestamp)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(.secondary)
                .frame(width: 60, alignment: .leading)

            Text(log.message)
                .font(.system(size: 11))
                .foregroundColor(.primary)
        }
    }
}

// MARK: - Models

enum SidebarTab {
    case columns
    case logs
}

struct SidebarColumnInfo: Identifiable {
    let id = UUID()
    let name: String
    let type: String
    let isClickable: Bool

    static let mock = [
        SidebarColumnInfo(name: "id", type: "INTEGER", isClickable: true),
        SidebarColumnInfo(name: "name", type: "TEXT", isClickable: true),
        SidebarColumnInfo(name: "email", type: "TEXT", isClickable: true),
        SidebarColumnInfo(name: "created_at", type: "TIMESTAMP", isClickable: true)
    ]
}

struct LogEntry: Identifiable {
    let id = UUID()
    let timestamp: String
    let message: String
    let level: LogLevel

    enum LogLevel {
        case info
        case warning
        case error
    }
}

// MARK: - Preview

#Preview {
    SidebarTabs()
        .frame(width: 320, height: 600)
}
