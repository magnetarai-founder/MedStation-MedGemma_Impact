import Foundation

// MARK: - Saved Query

struct SavedQuery: Codable, Identifiable {
    let id: Int
    let name: String
    let query: String
    let tags: [String]?
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case query
        case tags
        case createdAt = "created_at"
        case updatedAt = "updated_at"
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

    enum CodingKeys: String, CodingKey {
        case theme
        case defaultWorkspace = "default_workspace"
        case enableNotifications = "enable_notifications"
        case enableAnalytics = "enable_analytics"
    }

    static let `default` = AppSettings(
        theme: "auto",
        defaultWorkspace: "database",
        enableNotifications: true,
        enableAnalytics: false
    )
}
