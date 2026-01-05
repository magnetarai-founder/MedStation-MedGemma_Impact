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
            self.activeWorkspace = .chat  // Default to AI Chat
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

enum Workspace: String, CaseIterable, Identifiable, Hashable {
    case team
    case chat
    case code
    case database
    case kanban
    case insights
    case trust
    case magnetarHub

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .team: return "Team"
        case .chat: return "Chat"
        case .code: return "Code"
        case .database: return "Database"
        case .kanban: return "Kanban"
        case .insights: return "Insights"
        case .trust: return "MagnetarTrust"
        case .magnetarHub: return "MagnetarHub"
        }
    }

    var icon: String {
        switch self {
        case .team: return "person.2"
        case .chat: return "bubble.left"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .database: return "cylinder"
        case .kanban: return "square.grid.2x2"
        case .insights: return "waveform"
        case .trust: return "network"
        case .magnetarHub: return "cube.box"
        }
    }

    var keyboardShortcut: String {
        switch self {
        case .team: return "1"
        case .chat: return "2"
        case .code: return "3"
        case .database: return "4"
        case .kanban: return "5"
        case .insights: return "6"
        case .trust: return "7"
        case .magnetarHub: return "8"
        }
    }

    var shortName: String {
        switch self {
        case .team: return "Team"
        case .chat: return "Chat"
        case .code: return "Code"
        case .database: return "Data"
        case .kanban: return "Board"
        case .insights: return "Voice"
        case .trust: return "Trust"
        case .magnetarHub: return "Hub"
        }
    }

    /// Icon used in NavigationRail (may differ from generic icon for visual design)
    var railIcon: String {
        switch self {
        case .team: return "briefcase"
        case .chat: return "message"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .database: return "cylinder"
        case .kanban: return "square.grid.3x2"
        case .insights: return "waveform"
        case .trust: return "checkmark.shield"
        case .magnetarHub: return "crown"
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

    /// Workspaces in top rail cluster (ordered)
    static var topRailWorkspaces: [Workspace] {
        allCases.filter { $0.railPosition == .top }
    }

    /// Workspaces in bottom rail cluster (ordered)
    static var bottomRailWorkspaces: [Workspace] {
        allCases.filter { $0.railPosition == .bottom }
    }
}
