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

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .notes: return "Notes"
        case .docs: return "Docs"
        case .sheets: return "Sheets"
        case .pdf: return "PDFs"
        case .voice: return "Voice"
        }
    }

    var icon: String {
        switch self {
        case .notes: return "note.text"
        case .docs: return "doc.richtext"
        case .sheets: return "tablecells"
        case .pdf: return "doc.viewfinder"
        case .voice: return "waveform"
        }
    }

    var keyboardShortcut: KeyEquivalent? {
        switch self {
        case .notes: return nil
        case .docs: return nil
        case .sheets: return nil
        case .pdf: return nil
        case .voice: return nil
        }
    }
}
