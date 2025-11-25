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
    var activeWorkspace: Workspace = .database  // Default to Database (matching React)
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
    case magnetarHub

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .team: return "Team"
        case .chat: return "Chat"
        case .database: return "Database"
        case .kanban: return "Kanban"
        case .magnetarHub: return "MagnetarHub"
        }
    }

    var icon: String {
        switch self {
        case .team: return "person.2"
        case .chat: return "bubble.left"
        case .database: return "cylinder"
        case .kanban: return "square.grid.2x2"
        case .magnetarHub: return "cube.box"
        }
    }

    var keyboardShortcut: String {
        switch self {
        case .team: return "1"
        case .chat: return "2"
        case .database: return "3"
        case .kanban: return "4"
        case .magnetarHub: return "5"
        }
    }

    var shortName: String {
        switch self {
        case .team: return "Team"
        case .chat: return "Chat"
        case .database: return "Data"
        case .kanban: return "Board"
        case .magnetarHub: return "Hub"
        }
    }
}
