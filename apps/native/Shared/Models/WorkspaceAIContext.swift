//
//  WorkspaceAIContext.swift
//  MedStation
//
//  Workspace AI context types for the detached AI assistant window.
//  Each context represents a workspace domain with its own sessions and model override.
//

import SwiftUI

enum WorkspaceAIContext: String, CaseIterable, Identifiable, Codable, Sendable {
    case code
    case writing
    case sheets
    case voice
    case medical
    case general

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .code: return "Code"
        case .writing: return "Writing"
        case .sheets: return "Sheets"
        case .voice: return "Voice"
        case .medical: return "Medical"
        case .general: return "General"
        }
    }

    var icon: String {
        switch self {
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .writing: return "doc.text"
        case .sheets: return "tablecells"
        case .voice: return "waveform"
        case .medical: return "cross.case"
        case .general: return "sparkles"
        }
    }

    /// Context-specific system prompt prefix injected into AI requests
    var systemPromptPrefix: String? {
        switch self {
        case .code:
            return "You are a coding assistant. Help with programming, debugging, code review, and software architecture. Provide code examples in the user's language when relevant."
        case .writing:
            return "You are a writing assistant. Help with drafting, editing, tone, grammar, and style. Be clear and concise in suggestions."
        case .sheets:
            return "You are a spreadsheet and data assistant. Help with formulas, data analysis, calculations, and data transformation. Use formula syntax when applicable."
        case .voice:
            return "You are a voice and transcription assistant. Help with cleaning up transcriptions, summarizing audio content, and extracting key points."
        case .medical:
            return "You are a medical AI assistant powered by MedGemma. Help with medical triage, symptom analysis, differential diagnosis, and clinical reasoning. Always include appropriate medical disclaimers. This is for educational and informational purposes only — not a substitute for professional medical advice."
        case .general:
            return nil  // No additional context — use global system prompt only
        }
    }
}
