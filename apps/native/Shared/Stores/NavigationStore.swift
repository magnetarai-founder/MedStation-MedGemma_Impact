//
//  NavigationStore.swift
//  MagnetarStudio
//
//  Manages active workspace/tab navigation.
//

import Foundation
import Observation

@Observable
final class NavigationStore {
    var activeWorkspace: Workspace = .chat
    var isSidebarVisible: Bool = true

    func navigate(to workspace: Workspace) {
        activeWorkspace = workspace
    }

    func toggleSidebar() {
        isSidebarVisible.toggle()
    }
}

// MARK: - Workspace Enum

enum Workspace: String, CaseIterable, Identifiable, Hashable {
    case team
    case chat
    case database
    case kanban

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .team: return "Team"
        case .chat: return "Chat"
        case .database: return "Database"
        case .kanban: return "Kanban"
        }
    }

    var icon: String {
        switch self {
        case .team: return "person.2"
        case .chat: return "bubble.left"
        case .database: return "cylinder"
        case .kanban: return "square.grid.2x2"
        }
    }

    var keyboardShortcut: String {
        switch self {
        case .team: return "1"
        case .chat: return "2"
        case .database: return "3"
        case .kanban: return "4"
        }
    }
}
