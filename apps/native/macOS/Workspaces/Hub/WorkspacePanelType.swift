//
//  WorkspacePanelType.swift
//  MagnetarStudio
//
//  Panel types available in the Workspace Hub.
//

import SwiftUI

enum WorkspacePanelType: String, CaseIterable, Identifiable, Hashable {
    case notes
    case docs
    case sheets
    case pdf
    case voice
    case team
    case automations
    case plugins

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .notes: return "Notes"
        case .docs: return "Docs"
        case .sheets: return "Sheets"
        case .pdf: return "PDFs"
        case .voice: return "Voice"
        case .team: return "Team"
        case .automations: return "Automations"
        case .plugins: return "Plugins"
        }
    }

    var icon: String {
        switch self {
        case .notes: return "note.text"
        case .docs: return "doc.richtext"
        case .sheets: return "tablecells"
        case .pdf: return "doc.viewfinder"
        case .voice: return "waveform"
        case .team: return "bubble.left.and.text.bubble.right"
        case .automations: return "gearshape.2"
        case .plugins: return "puzzlepiece.extension"
        }
    }

    // MARK: - Grouping

    /// Content creation panels (always shown)
    static var contentPanels: [WorkspacePanelType] {
        [.notes, .docs, .sheets, .pdf, .voice]
    }

    /// Management/configuration panels
    static var managementPanels: [WorkspacePanelType] {
        [.automations, .plugins]
    }

    /// Shortcut hint displayed in sidebar (within Workspace tab context)
    var shortcutHint: String {
        switch self {
        case .notes: return "N"
        case .docs: return "D"
        case .sheets: return "S"
        case .pdf: return "P"
        case .voice: return "V"
        case .team: return "T"
        case .automations: return "A"
        case .plugins: return "X"
        }
    }
}
