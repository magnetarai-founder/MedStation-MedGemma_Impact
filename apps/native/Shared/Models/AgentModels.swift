//
//  AgentModels.swift
//  MagnetarStudio
//
//  Models for Agent API integration
//  Matches backend /api/v1/agent/* endpoint schemas
//

import Foundation

// MARK: - Route Request/Response

/// Request to route user input and determine intent
struct AgentRouteRequest: Codable {
    let input: String
    let session_id: String?

    init(input: String, session_id: String? = nil) {
        self.input = input
        self.session_id = session_id
    }
}

/// Response from route endpoint with intent classification
struct AgentRouteResponse: Codable {
    let intent: String              // "code_edit", "shell", "question"
    let confidence: Float           // 0.0-1.0
    let model_hint: String?         // Suggested model (e.g., "qwen2.5-coder:32b")
    let next_action: String         // "call /agent/plan" or "answer directly"
    let learning_used: Bool?        // Whether learning system influenced decision
}
