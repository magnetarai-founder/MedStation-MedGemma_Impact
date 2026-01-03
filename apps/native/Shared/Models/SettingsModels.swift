import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SettingsModels")

// MARK: - Saved Query

struct SavedQuery: Codable, Identifiable {
    let id: Int
    let name: String
    let query: String
    let queryType: String?
    let folder: String?
    let description: String?
    let tags: [String]?
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case query
        case queryType = "query_type"
        case folder
        case description
        case tags
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        // Required fields
        id = try container.decode(Int.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        query = try container.decode(String.self, forKey: .query)

        // Optional fields
        queryType = try container.decodeIfPresent(String.self, forKey: .queryType)
        folder = try container.decodeIfPresent(String.self, forKey: .folder)
        description = try container.decodeIfPresent(String.self, forKey: .description)
        createdAt = try container.decodeIfPresent(String.self, forKey: .createdAt)
        updatedAt = try container.decodeIfPresent(String.self, forKey: .updatedAt)

        // Parse tags - backend returns JSON string, we need array
        if let tagsString = try container.decodeIfPresent(String.self, forKey: .tags),
           !tagsString.isEmpty,
           let tagsData = tagsString.data(using: .utf8),
           let tagsArray = try? JSONDecoder().decode([String].self, from: tagsData) {
            tags = tagsArray
        } else {
            tags = nil
        }

        logger.debug("Decoded SavedQuery - id: \(id), name: \(name), queryType: \(queryType ?? "nil")")
    }
}

// MARK: - Chat Settings

struct ChatSettings: Codable {
    var defaultModel: String
    var temperature: Double
    var topP: Double
    var topK: Int
    var repeatPenalty: Double
    var autoGenerateTitles: Bool
    var autoPreloadModel: Bool

    enum CodingKeys: String, CodingKey {
        case defaultModel = "default_model"
        case temperature
        case topP = "top_p"
        case topK = "top_k"
        case repeatPenalty = "repeat_penalty"
        case autoGenerateTitles = "auto_generate_titles"
        case autoPreloadModel = "auto_preload_model"
    }

    // Default settings
    static let `default` = ChatSettings(
        defaultModel: "mistral",
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
        repeatPenalty: 1.1,
        autoGenerateTitles: true,
        autoPreloadModel: false
    )
}

// MARK: - App Settings

struct AppSettings: Codable {
    var theme: String  // "light" | "dark" | "auto"
    var defaultWorkspace: String  // "database" | "chat" | "team" | "kanban"
    var enableNotifications: Bool
    var enableAnalytics: Bool
    var ollamaAutoStart: Bool  // Auto-start Ollama on app launch

    enum CodingKeys: String, CodingKey {
        case theme
        case defaultWorkspace = "default_workspace"
        case enableNotifications = "enable_notifications"
        case enableAnalytics = "enable_analytics"
        case ollamaAutoStart = "ollama_auto_start"
    }

    static let `default` = AppSettings(
        theme: "auto",
        defaultWorkspace: "database",
        enableNotifications: true,
        enableAnalytics: false,
        ollamaAutoStart: true  // Default ON
    )
}
