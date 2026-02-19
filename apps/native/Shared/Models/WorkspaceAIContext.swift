//
//  WorkspaceAIContext.swift
//  MedStation
//
//  AI context types for the detached AI assistant window.
//

import SwiftUI

enum WorkspaceAIContext: String, CaseIterable, Identifiable, Codable, Sendable {
    case medical
    case general

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .medical: return "Medical"
        case .general: return "General"
        }
    }

    var icon: String {
        switch self {
        case .medical: return "cross.case"
        case .general: return "sparkles"
        }
    }

    var systemPromptPrefix: String? {
        switch self {
        case .medical:
            return "You are a medical AI assistant powered by MedGemma. Help with medical triage, symptom analysis, differential diagnosis, and clinical reasoning. Always include appropriate medical disclaimers. This is for educational and informational purposes only — not a substitute for professional medical advice."
        case .general:
            return nil
        }
    }
}
