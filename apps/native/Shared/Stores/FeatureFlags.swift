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

    // Team workspace - future
    var team: Bool = false

    private init() {}
}
