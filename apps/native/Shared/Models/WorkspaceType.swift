//
//  WorkspaceType.swift
//  MedStation
//
//  Workspace type identifiers.
//

import Foundation

enum WorkspaceType: String, Codable, CaseIterable, Sendable {
    case chat
    case hub
    case medical
    case settings

    var displayName: String {
        switch self {
        case .chat: return "AI Chat"
        case .hub: return "Hub"
        case .medical: return "Medical AI"
        case .settings: return "Settings"
        }
    }
}
