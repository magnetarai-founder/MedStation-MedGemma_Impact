//
//  NavigationStore.swift
//  MagnetarStudio
//
//  SPDX-License-Identifier: Proprietary
//

import Foundation
import Observation

// MARK: - NavigationStore

/// Central state management for workspace navigation.
///
/// ## Overview
/// NavigationStore manages which workspace is active and sidebar visibility.
/// Works with the `Workspace` enum to provide a single source of truth for
/// navigation state across the app.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Non-Singleton**: Created per-window, but typically one instance
///
/// ## State Persistence (UserDefaults)
/// - `activeWorkspace` - Last active workspace tab (defaults to `.chat`)
/// - `isSidebarVisible` - Sidebar collapsed/expanded state (defaults to `true`)
///
/// ## Integration with Workspace Enum
/// The `Workspace` enum defines all available workspaces with properties for:
/// - `displayName` - Human-readable name
/// - `icon` - SF Symbol for general use
/// - `railIcon` - SF Symbol for NavigationRail (may differ)
/// - `keyboardShortcut` - ⌘1-8 shortcuts
/// - `railPosition` - Top or bottom cluster in NavigationRail
///
/// ## Usage
/// ```swift
/// // In app root
/// @State private var navigationStore = NavigationStore()
///
/// // Navigate to workspace
/// navigationStore.navigate(to: .vault)
///
/// // Toggle sidebar
/// navigationStore.toggleSidebar()
///
/// // Read current workspace
/// if navigationStore.activeWorkspace == .chat { ... }
/// ```
@MainActor
@Observable
final class NavigationStore {
    private static let workspaceKey = "magnetar.lastActiveWorkspace"
    private static let sidebarKey = "magnetar.isSidebarVisible"

    var activeWorkspace: Workspace {
        didSet {
            saveWorkspaceState()
        }
    }

    var isSidebarVisible: Bool {
        didSet {
            saveSidebarState()
        }
    }

    init() {
        // Restore last active workspace or default to chat
        if let savedWorkspace = UserDefaults.standard.string(forKey: Self.workspaceKey),
           let workspace = Workspace(rawValue: savedWorkspace) {
            self.activeWorkspace = workspace
        } else {
            self.activeWorkspace = .workspace  // Default to Workspace Hub
        }

        // Restore sidebar visibility (default to true)
        self.isSidebarVisible = UserDefaults.standard.object(forKey: Self.sidebarKey) as? Bool ?? true
    }

    func navigate(to workspace: Workspace) {
        activeWorkspace = workspace
    }

    func toggleSidebar() {
        isSidebarVisible.toggle()
    }

    // MARK: - State Persistence

    private func saveWorkspaceState() {
        UserDefaults.standard.set(activeWorkspace.rawValue, forKey: Self.workspaceKey)
    }

    private func saveSidebarState() {
        UserDefaults.standard.set(isSidebarVisible, forKey: Self.sidebarKey)
    }
}

// MARK: - Workspace Enum

// MARK: - Workspace Enum
//
// Phase 2B: Simplified to core workspaces (Chat, Files) with others as spawnable windows
// Core tabs (always visible): chat, files
// Spawnable windows (via menu/shortcuts): code, kanban, team, database, insights, trust, magnetarHub

enum Workspace: String, CaseIterable, Identifiable, Hashable {
    // Core workspaces (3 tabs in header)
    case chat
    case files
    case workspace  // Workspace Hub — Notes, Docs, Sheets, PDFs, Voice

    // Spawnable workspaces (open as separate windows via + menu)
    case code  // Code IDE workspace (full IDE with terminal bridge)
    case database
    case kanban
    case insights
    case trust
    case magnetarHub

    // Legacy - keeping for transition, redirects to workspace tab
    case team

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .chat: return "Chat"
        case .files: return "Files"
        case .workspace: return "Workspace"
        case .code: return "Code IDE"
        case .database: return "Data"
        case .kanban: return "Kanban"
        case .insights: return "Insights"
        case .trust: return "MagnetarTrust"
        case .magnetarHub: return "MagnetarHub"
        case .team: return "Team"  // Legacy
        }
    }

    var icon: String {
        switch self {
        case .chat: return "bubble.left"
        case .files: return "folder"
        case .workspace: return "square.grid.2x2"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .database: return "cylinder"
        case .kanban: return "square.grid.3x3"
        case .insights: return "waveform"
        case .trust: return "network"
        case .magnetarHub: return "cube.box"
        case .team: return "person.2"  // Legacy
        }
    }

    var keyboardShortcut: String {
        switch self {
        case .workspace: return "1"
        case .files: return "2"
        case .code: return "3"
        case .chat: return "4"
        case .database: return "5"
        case .kanban: return "6"
        case .insights: return "7"
        case .trust: return "8"
        case .magnetarHub: return "9"
        case .team: return ""  // Legacy - no shortcut
        }
    }

    var shortName: String {
        switch self {
        case .chat: return "Chat"
        case .files: return "Files"
        case .workspace: return "Hub"
        case .code: return "Code"
        case .database: return "Data"
        case .kanban: return "Board"
        case .insights: return "Voice"
        case .trust: return "Trust"
        case .magnetarHub: return "Hub"
        case .team: return "Team"  // Legacy
        }
    }

    /// Icon used in NavigationRail/Tab switcher
    var railIcon: String {
        switch self {
        case .chat: return "message"
        case .files: return "folder.fill"
        case .workspace: return "square.grid.2x2.fill"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .database: return "cylinder"
        case .kanban: return "square.grid.3x2"
        case .insights: return "waveform"
        case .trust: return "checkmark.shield"
        case .magnetarHub: return "crown"
        case .team: return "briefcase"  // Legacy
        }
    }

    /// Whether this is a core workspace (shown in tab switcher) or spawnable (opens in separate window)
    var isCore: Bool {
        switch self {
        case .chat, .files, .workspace, .code: return true
        default: return false
        }
    }

    /// Position in NavigationRail - top cluster or bottom cluster
    enum RailPosition {
        case top
        case bottom
    }

    var railPosition: RailPosition {
        switch self {
        case .magnetarHub: return .bottom
        default: return .top
        }
    }

    /// Core workspaces shown in main tab switcher (4 tabs)
    static var coreWorkspaces: [Workspace] {
        [.workspace, .files, .code, .chat]
    }

    /// Spawnable workspaces that open as separate windows (Phase 2C)
    static var spawnableWorkspaces: [Workspace] {
        allCases.filter { !$0.isCore }
    }

    /// Workspaces in top rail cluster (ordered) - legacy, keeping for transition
    static var topRailWorkspaces: [Workspace] {
        allCases.filter { $0.railPosition == .top }
    }

    /// Workspaces in bottom rail cluster (ordered) - legacy, keeping for transition
    static var bottomRailWorkspaces: [Workspace] {
        allCases.filter { $0.railPosition == .bottom }
    }

    /// Map to ANE WorkspaceType for cross-workspace learning
    var workspaceType: WorkspaceType? {
        switch self {
        case .chat: return .chat
        case .files: return .docs
        case .workspace: return .hub
        case .code: return .code
        case .database: return .data
        case .kanban: return .kanban
        case .insights: return .insights
        case .trust: return .vault
        case .magnetarHub: return .hub
        case .team: return .team
        }
    }
}
