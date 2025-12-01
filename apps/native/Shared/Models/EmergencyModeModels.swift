//
//  EmergencyModeModels.swift
//  MagnetarStudio
//
//  Emergency mode shared types and models
//

import Foundation

/// Methods for triggering emergency mode
public enum EmergencyTriggerMethod: String {
    case textConfirmation = "text_confirmation"  // "I UNDERSTAND"
    case keyCombo = "key_combo"                  // Cmd+Shift+Delete (5 sec)
}

/// Report of emergency wipe results
public struct EmergencyWipeReport: Codable {
    public var simulated: Bool
    public var filesWiped: Int
    public var passes: Int
    public var durationSeconds: TimeInterval
    public var errors: [String]
    public var filesIdentified: [String]

    public init(simulated: Bool, filesWiped: Int, passes: Int, durationSeconds: TimeInterval, errors: [String], filesIdentified: [String] = []) {
        self.simulated = simulated
        self.filesWiped = filesWiped
        self.passes = passes
        self.durationSeconds = durationSeconds
        self.errors = errors
        self.filesIdentified = filesIdentified
    }

    enum CodingKeys: String, CodingKey {
        case simulated
        case filesWiped = "files_wiped"
        case passes
        case durationSeconds = "duration_seconds"
        case errors
        case filesIdentified = "files_identified"
    }
}
