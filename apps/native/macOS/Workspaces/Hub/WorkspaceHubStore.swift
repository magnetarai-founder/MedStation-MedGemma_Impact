//
//  WorkspaceHubStore.swift
//  MagnetarStudio
//
//  State management for the Workspace Hub — tracks selected panel,
//  sidebar width, and open documents.
//

import Foundation
import Observation
import SwiftUI

@MainActor
@Observable
final class WorkspaceHubStore {
    static let shared = WorkspaceHubStore()

    // MARK: - Panel Selection

    var selectedPanel: WorkspacePanelType {
        didSet {
            UserDefaults.standard.set(selectedPanel.rawValue, forKey: "workspace.selectedPanel")
        }
    }

    // MARK: - Layout State

    @ObservationIgnored
    @AppStorage("workspace.sidebarWidth") var sidebarWidth: Double = 220

    // MARK: - Initialization

    init() {
        if let saved = UserDefaults.standard.string(forKey: "workspace.selectedPanel"),
           let panel = WorkspacePanelType(rawValue: saved) {
            self.selectedPanel = panel
        } else {
            self.selectedPanel = .notes
        }
    }

    // MARK: - Actions

    func selectPanel(_ panel: WorkspacePanelType) {
        selectedPanel = panel
    }
}
