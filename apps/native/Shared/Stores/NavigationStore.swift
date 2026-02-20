//
//  NavigationStore.swift
//  MedStation
//
//  SPDX-License-Identifier: CC-BY-4.0
//

import Foundation
import Observation

@MainActor
@Observable
final class NavigationStore {

    var activeWorkspace: Workspace = .workspace

    func navigate(to workspace: Workspace) {
        activeWorkspace = workspace
    }
}

enum Workspace: String, CaseIterable, Identifiable, Hashable {
    case workspace

    var id: String { rawValue }
    var displayName: String { "Medical AI" }
    var icon: String { "cross.case" }
}
