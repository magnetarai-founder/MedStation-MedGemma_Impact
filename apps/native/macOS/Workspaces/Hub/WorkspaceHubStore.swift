//
//  WorkspaceHubStore.swift
//  MedStation
//
//  State management for the Workspace Hub.
//

import Foundation
import Observation
import SwiftUI

@MainActor
@Observable
final class WorkspaceHubStore {
    static let shared = WorkspaceHubStore()

    var selectedPanel: WorkspacePanelType = .medical

    @ObservationIgnored
    @AppStorage("workspace.sidebarWidth") var sidebarWidth: Double = 220

    init() {
        self.selectedPanel = .medical
    }

    func selectPanel(_ panel: WorkspacePanelType) {
        selectedPanel = panel
    }
}
