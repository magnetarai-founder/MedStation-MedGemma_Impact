//
//  WorkspacePanelType.swift
//  MedStation
//
//  Panel types available in the Workspace Hub.
//

import SwiftUI

enum WorkspacePanelType: String, CaseIterable, Identifiable, Hashable {
    case medical

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .medical: return "Medical AI"
        }
    }

    var icon: String {
        switch self {
        case .medical: return "cross.case"
        }
    }

    static var contentPanels: [WorkspacePanelType] {
        [.medical]
    }

    static var managementPanels: [WorkspacePanelType] {
        []
    }

    var shortcutHint: String {
        switch self {
        case .medical: return "M"
        }
    }
}
