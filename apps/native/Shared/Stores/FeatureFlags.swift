//
//  FeatureFlags.swift
//  MedStation
//
//  Feature flags for MedStation.
//

import Foundation
import Observation

@MainActor
@Observable
final class FeatureFlags {
    static let shared = FeatureFlags()

    // Medical AI is always enabled
    let medical: Bool = true

    // Team workspace - future
    var team: Bool = false

    private init() {}

    func isWorkspaceEnabled(_ workspace: Workspace) -> Bool {
        return true
    }

    var enabledSpawnableWorkspaces: [Workspace] {
        []
    }
}
