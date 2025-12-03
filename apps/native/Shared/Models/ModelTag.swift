//
//  ModelTag.swift
//  MagnetarStudio
//
//  Model tag system for categorizing model capabilities
//  Supports auto-detection and manual overrides
//

import SwiftUI

// MARK: - Tag Definition

struct ModelTag: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let description: String
    let icon: String  // SF Symbol name

    var color: Color {
        tagColor(for: id)
    }
}

// MARK: - Model Tags Response

struct ModelTagsResponse: Codable {
    let modelName: String
    let tags: [String]
    let autoDetected: [String]
    let manualOverride: Bool

    enum CodingKeys: String, CodingKey {
        case modelName = "model_name"
        case tags
        case autoDetected = "auto_detected"
        case manualOverride = "manual_override"
    }
}

// MARK: - Update Tags Request

struct UpdateTagsRequest: Codable {
    let tags: [String]
}

// MARK: - Tag Colors

func tagColor(for tagId: String) -> Color {
    switch tagId {
    // Core capabilities
    case "general":
        return .gray
    case "chat":
        return .purple
    case "code":
        return .blue
    case "reasoning":
        return .green
    case "deep-reasoning":
        return .teal
    case "math":
        return .orange
    case "data":
        return .cyan
    case "orchestration":
        return .indigo

    // Specialized
    case "vision":
        return .pink
    case "creative":
        return .yellow
    case "function-calling":
        return .mint
    case "multilingual":
        return .brown

    default:
        return .secondary
    }
}

// MARK: - Tag Categories (for grouping in UI)

enum TagCategory: String, CaseIterable {
    case core = "Core Capabilities"
    case specialized = "Specialized"

    func tags(from allTags: [ModelTag]) -> [ModelTag] {
        let coreIds = ["general", "chat", "code", "reasoning", "deep-reasoning", "math", "data", "orchestration"]

        switch self {
        case .core:
            return allTags.filter { coreIds.contains($0.id) }
        case .specialized:
            return allTags.filter { !coreIds.contains($0.id) }
        }
    }
}
