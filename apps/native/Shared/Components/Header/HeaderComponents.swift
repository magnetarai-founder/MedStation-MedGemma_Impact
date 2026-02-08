//
//  HeaderComponents.swift
//  MagnetarStudio
//
//  Reusable header UI components - Extracted from Header.swift
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HeaderComponents")

// MARK: - Brand Cluster

struct BrandCluster: View {
    var body: some View {
        Text("MagnetarStudio")
            .font(.system(size: 22, weight: .bold))
            .foregroundStyle(.primary)
    }
}

// MARK: - Panic Button (Simplified from ControlCluster)

struct PanicButton: View {
    @Binding var showPanicMode: Bool
    @Binding var showEmergencyMode: Bool

    @State private var clickCount: Int = 0
    @State private var lastClickTime: Date = Date.distantPast

    var body: some View {
        HeaderToolbarButton(
            icon: "exclamationmark.triangle.fill",
            tint: Color.red.opacity(0.9),
            background: Color.red.opacity(0.12)
        ) {
            handlePanicButtonClick()
        }
        .help("Panic Mode (Double-click) / Emergency Mode (Triple-click)")
    }

    private func handlePanicButtonClick() {
        let now = Date()
        let timeSinceLastClick = now.timeIntervalSince(lastClickTime)

        if timeSinceLastClick > 1.0 {
            clickCount = 1
        } else {
            clickCount += 1
        }

        lastClickTime = now

        logger.debug("Panic button clicked (\(clickCount) clicks)")

        if clickCount == 2 {
            logger.info("Opening standard panic mode")
            showPanicMode = true
            clickCount = 0
        } else if clickCount >= 3 {
            logger.warning("Opening EMERGENCY MODE")
            showEmergencyMode = true
            clickCount = 0
        }
    }
}

// MARK: - Header Toolbar Button

struct HeaderToolbarButton: View {
    let icon: String
    var label: String? = nil
    var tint: Color = .primary
    var background: Color = Color.white.opacity(0.12)
    let action: () -> Void

    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))

                if let label {
                    Text(label)
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.trailing, 2)
                }
            }
            .foregroundStyle(tint.opacity(isHovering ? 1.0 : 0.85))
            .padding(.horizontal, label == nil ? 10 : 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(background.opacity(isHovering ? 1.0 : 0.8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Color.white.opacity(0.18), lineWidth: 0.6)
                    )
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Activity Monitor Tile

struct ActivityMonitorTile: View {
    let stats: SystemStats

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("System Resources")
                .font(.system(size: 15, weight: .semibold))

            VStack(spacing: 16) {
                ResourceRow(icon: "cpu", label: "CPU", percentage: stats.cpuUsage, color: .blue)
                ResourceRow(icon: "memorychip", label: "Memory", percentage: stats.memoryUsage, color: .green)
                ResourceRow(icon: "internaldrive", label: "Disk", percentage: stats.diskUsage, color: .orange)

                HStack(spacing: 12) {
                    Image(systemName: "network")
                        .font(.system(size: 18))
                        .foregroundStyle(.purple)
                        .frame(width: 28)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Network")
                            .font(.system(size: 13, weight: .medium))

                        HStack(spacing: 12) {
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.down")
                                    .font(.system(size: 10))
                                Text(stats.networkIn)
                                    .font(.system(size: 11))
                            }
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.up")
                                    .font(.system(size: 10))
                                Text(stats.networkOut)
                                    .font(.system(size: 11))
                            }
                        }
                        .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 24)
            }
        }
        .padding(16)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Control Center Button

struct ControlCenterButton: View {
    let icon: String
    let label: String
    let color: Color
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.15))
                        .frame(width: 52, height: 52)

                    Image(systemName: icon)
                        .font(.system(size: 22))
                        .foregroundStyle(color)
                }

                Text(label)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.primary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isHovered ? Color.secondary.opacity(0.08) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.magnetarQuick) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Network Status Row

struct NetworkStatusRow: View {
    let icon: String
    let label: String
    let status: String
    let isActive: Bool

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundStyle(isActive ? Color.magnetarPrimary : .secondary)
                .frame(width: 28)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.primary)

                Text(status)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            Spacer()

            if isActive {
                Circle()
                    .fill(Color.green)
                    .frame(width: 8, height: 8)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isHovered ? Color.secondary.opacity(0.08) : Color.clear)
        )
        .onHover { hovering in
            withAnimation(.magnetarQuick) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Resource Row

struct ResourceRow: View {
    let icon: String
    let label: String
    let percentage: Double
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundStyle(color)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(label)
                        .font(.system(size: 14, weight: .medium))
                    Spacer()
                    Text("\(Int(percentage))%")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                }

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(height: 6)
                            .cornerRadius(3)

                        Rectangle()
                            .fill(color)
                            .frame(width: geometry.size.width * (percentage / 100), height: 6)
                            .cornerRadius(3)
                    }
                }
                .frame(height: 6)
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.horizontal, 24)
    }
}

// MARK: - Security Action Row

struct SecurityActionRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundStyle(.red)
                .frame(width: 20)

            Text(text)
                .font(.system(size: 13))
                .foregroundStyle(.primary)

            Spacer()
        }
    }
}

// MARK: - Workspace Tabs (Phase 2B)
//
// Simple tab switcher for core workspaces: Chat, Files
// Replaces the 8-icon NavigationRail with a clean, minimal design

struct WorkspaceTabs: View {
    @Environment(NavigationStore.self) private var navigationStore

    var body: some View {
        HStack(spacing: 4) {
            ForEach(Workspace.coreWorkspaces) { workspace in
                WorkspaceTab(
                    workspace: workspace,
                    isActive: navigationStore.activeWorkspace == workspace
                ) {
                    navigationStore.activeWorkspace = workspace
                }
            }
        }
        .padding(4)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color.white.opacity(0.08))
        )
    }
}

// MARK: - Single Workspace Tab

struct WorkspaceTab: View {
    let workspace: Workspace
    let isActive: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: workspace.railIcon)
                    .font(.system(size: 14, weight: .medium))

                Text(workspace.shortName)
                    .font(.system(size: 13, weight: .medium))
            }
            .foregroundStyle(isActive ? .white : (isHovered ? .primary : .secondary))
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(isActive ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.12) : Color.clear))
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .help("\(workspace.displayName) (⌘\(workspace.keyboardShortcut))")
    }
}

// MARK: - Quick Action Button (Phase 2B/2C/2D)
//
// CREATE section: Opens new notes/chats in detached windows
// OPEN WORKSPACE section: Opens power workspaces in separate windows

struct QuickActionButton: View {
    @Environment(\.openWindow) private var openWindow
    @State private var isHovered = false

    private var featureFlags: FeatureFlags { FeatureFlags.shared }

    var body: some View {
        Menu {
            // MARK: - Create Section
            Section {
                Button {
                    openWindow(id: "detached-note")
                    logger.info("Opening new detached note window")
                } label: {
                    Label("New Note", systemImage: "doc.text")
                }
                .keyboardShortcut("n", modifiers: [.command, .shift])

                Button {
                    openWindow(id: "detached-chat")
                    logger.info("Opening new detached chat window")
                } label: {
                    Label("New Chat", systemImage: "bubble.left.and.bubble.right")
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])

                Button {
                    let info = DetachedDocEditInfo(title: "Untitled Document")
                    openWindow(value: info)
                    logger.info("Opening new document window")
                } label: {
                    Label("New Document", systemImage: "doc.richtext")
                }

                Button {
                    let info = DetachedSheetInfo(title: "Untitled Spreadsheet")
                    openWindow(value: info)
                    logger.info("Opening new spreadsheet window")
                } label: {
                    Label("New Spreadsheet", systemImage: "tablecells")
                }
            } header: {
                Text("Create")
            }

            // MARK: - Open in New Window Section
            Section {
                // Code IDE pop-out (always available — ⌘3 navigates to tab)
                Button {
                    openSpawnableWorkspace(.code)
                } label: {
                    Label("Code IDE", systemImage: Workspace.code.icon)
                }

                // Other enabled spawnable workspaces
                ForEach(featureFlags.enabledSpawnableWorkspaces.filter { $0 != .code }) { workspace in
                    Button {
                        openSpawnableWorkspace(workspace)
                    } label: {
                        Label(workspace.displayName, systemImage: workspace.icon)
                    }
                    .keyboardShortcut(KeyEquivalent(Character(workspace.keyboardShortcut)), modifiers: .command)
                }
            } header: {
                Text("Open in New Window")
            }

            // MARK: - Admin (role-gated)
            if let role = AuthStore.shared.user?.userRole,
               [.founderRights, .superAdmin, .admin].contains(role) {
                Section {
                    Button {
                        WindowOpener.shared.openAdmin()
                    } label: {
                        Label("Founder Admin", systemImage: "shield.lefthalf.filled")
                    }
                } header: {
                    Text("Admin")
                }
            }

            // MARK: - Settings
            Divider()
            Button {
                UserDefaults.standard.set(SettingsTab.features.rawValue, forKey: "settings.selectedTab")
                NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
            } label: {
                Label("Manage Features...", systemImage: "puzzlepiece.extension")
            }
        } label: {
            Image(systemName: "plus")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(isHovered ? .primary : .secondary)
                .padding(8)
                .background(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(isHovered ? Color.white.opacity(0.15) : Color.white.opacity(0.08))
                )
        }
        .menuStyle(.borderlessButton)
        .menuIndicator(.hidden)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .help("Create new or open workspace (⇧⌘N)")
    }

    private func openSpawnableWorkspace(_ workspace: Workspace) {
        let windowId = windowIdForWorkspace(workspace)
        openWindow(id: windowId)
        logger.info("Opening spawnable workspace: \(workspace.displayName)")
    }

    private func windowIdForWorkspace(_ workspace: Workspace) -> String {
        switch workspace {
        case .code: return "workspace-code"
        case .team: return "workspace-team"
        case .kanban: return "workspace-kanban"
        case .database: return "workspace-database"
        case .insights: return "workspace-insights"
        case .trust: return "workspace-trust"
        case .magnetarHub: return "workspace-hub"
        default: return "workspace-\(workspace.rawValue)"
        }
    }
}

// MARK: - AI Toggle Button

struct AIToggleButton: View {
    var body: some View {
        HeaderToolbarButton(
            icon: "sparkles",
            tint: .purple,
            background: Color.purple.opacity(0.15)
        ) {
            WindowOpener.shared.openAIAssistant()
        }
        .help("Open AI Assistant (⇧⌘P)")
        .keyboardShortcut("p", modifiers: [.command, .shift])
    }
}
