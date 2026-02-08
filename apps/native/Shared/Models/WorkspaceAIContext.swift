//
//  WorkspaceAIContext.swift
//  MagnetarStudio
//
//  Workspace AI context types for the detached AI assistant window.
//  Each context represents a workspace domain with its own sessions and model override.
//

import SwiftUI

enum WorkspaceAIContext: String, CaseIterable, Identifiable, Codable, Sendable {
    case code
    case writing
    case sheets
    case voice
    case general

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .code: return "Code"
        case .writing: return "Writing"
        case .sheets: return "Sheets"
        case .voice: return "Voice"
        case .general: return "General"
        }
    }

    var icon: String {
        switch self {
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .writing: return "doc.text"
        case .sheets: return "tablecells"
        case .voice: return "waveform"
        case .general: return "sparkles"
        }
    }
}
