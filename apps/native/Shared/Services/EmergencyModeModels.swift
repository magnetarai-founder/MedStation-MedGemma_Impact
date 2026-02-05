//
//  EmergencyModeModels.swift
//  MagnetarStudio
//
//  Supporting types for EmergencyModeService
//  Extracted for cleaner organization
//

import Foundation

// MARK: - Emergency Wipe Report

struct EmergencyWipeReport {
    var simulated: Bool
    var filesWiped: Int
    var passes: Int
    var durationSeconds: Double
    var errors: [String]
    var filesIdentified: [String] = []

    var success: Bool {
        errors.isEmpty
    }
}

// MARK: - Trigger Methods

enum EmergencyTriggerMethod: String {
    case tripleClick = "triple_click"
    case panicButton = "panic_button"
    case deadManSwitch = "dead_man_switch"
    case remote = "remote_trigger"
    case textConfirmation = "text_confirmation"  // "I UNDERSTAND" text entry
    case keyCombo = "key_combo"                  // Cmd+Shift+Delete (5 sec hold)
}

// MARK: - Backend Response

struct BackendEmergencyResponse: Codable, Sendable {
    let success: Bool
    let filesWiped: Int
    let passes: Int
    let durationSeconds: Double
    let errors: [String]

    enum CodingKeys: String, CodingKey {
        case success
        case filesWiped = "files_wiped"
        case passes
        case durationSeconds = "duration_seconds"
        case errors
    }
}

// MARK: - Errors

enum EmergencyModeError: LocalizedError {
    case disabledInDebug
    case backendFailed
    case alreadyInProgress

    var errorDescription: String? {
        switch self {
        case .disabledInDebug:
            return "Emergency mode disabled in debug build (safety measure)"
        case .backendFailed:
            return "Backend emergency wipe failed"
        case .alreadyInProgress:
            return "Emergency mode already in progress"
        }
    }
}
