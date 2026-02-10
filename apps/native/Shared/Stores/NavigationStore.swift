//
//  NavigationStore.swift
//  MedStation
//
//  SPDX-License-Identifier: CC-BY-4.0
//

import Foundation
import Observation

// MARK: - NavigationStore

@MainActor
@Observable
final class NavigationStore {
    private static let workspaceKey = "medstation.lastActiveWorkspace"
    private static let sidebarKey = "medstation.isSidebarVisible"

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
        self.activeWorkspace = .workspace
        self.isSidebarVisible = true
    }

    func navigate(to workspace: Workspace) {
        activeWorkspace = workspace
    }

    func toggleSidebar() {
        isSidebarVisible.toggle()
    }

    private func saveWorkspaceState() {
        UserDefaults.standard.set(activeWorkspace.rawValue, forKey: Self.workspaceKey)
    }

    private func saveSidebarState() {
        UserDefaults.standard.set(isSidebarVisible, forKey: Self.sidebarKey)
    }
}

// MARK: - Workspace Enum

enum Workspace: String, CaseIterable, Identifiable, Hashable {
    case workspace  // Medical Hub — the main view

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .workspace: return "Medical AI"
        }
    }

    var icon: String {
        switch self {
        case .workspace: return "cross.case"
        }
    }

    var keyboardShortcut: String {
        switch self {
        case .workspace: return "1"
        }
    }

    var shortName: String {
        switch self {
        case .workspace: return "Medical"
        }
    }

    var railIcon: String {
        switch self {
        case .workspace: return "cross.case.fill"
        }
    }

    var isCore: Bool { true }

    enum RailPosition {
        case top
        case bottom
    }

    var railPosition: RailPosition { .top }

    static var coreWorkspaces: [Workspace] {
        [.workspace]
    }

    static var spawnableWorkspaces: [Workspace] {
        []
    }

    static var topRailWorkspaces: [Workspace] {
        allCases
    }

    static var bottomRailWorkspaces: [Workspace] {
        []
    }

    var workspaceType: WorkspaceType? {
        switch self {
        case .workspace: return .hub
        }
    }
}
