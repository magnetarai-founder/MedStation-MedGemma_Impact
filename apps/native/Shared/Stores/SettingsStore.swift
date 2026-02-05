import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SettingsStore")

// MARK: - SettingsStore

/// Central state management for app settings and saved queries.
///
/// ## Overview
/// SettingsStore manages user preferences, chat settings, and saved SQL queries.
/// Settings are persisted locally in UserDefaults while saved queries sync with
/// the backend.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `SettingsStore.shared`
///
/// ## State Persistence
/// **UserDefaults (Local):**
/// - `chatSettings` - Chat workspace preferences (streaming, context window, etc.)
/// - `appSettings` - App-wide preferences (theme, notifications, etc.)
///
/// **Backend (Synced):**
/// - `savedQueries` - User's saved SQL queries (Database workspace)
///
/// ## Settings Types
/// - `ChatSettings` - AI chat configuration (model defaults, context length, etc.)
/// - `AppSettings` - Application preferences (appearance, behavior)
/// - `SavedQuery` - Reusable SQL queries with tags
///
/// ## Dependencies
/// - `SettingsService` - Backend saved queries API
///
/// ## Usage
/// ```swift
/// let settings = SettingsStore.shared
///
/// // Update chat settings
/// settings.chatSettings.enableStreaming = true
/// settings.saveChatSettings()
///
/// // Load saved queries
/// await settings.loadSavedQueries()
///
/// // Save a new query
/// await settings.createSavedQuery(
///     name: "Monthly Sales",
///     query: "SELECT * FROM sales WHERE month = ?",
///     tags: ["sales", "reports"]
/// )
/// ```
@MainActor
@Observable
final class SettingsStore {
    static let shared = SettingsStore()

    // MARK: - Observable State

    var savedQueries: [SavedQuery] = []
    var chatSettings: ChatSettings
    var appSettings: AppSettings
    var isLoading = false
    var error: String?

    private let service = SettingsService.shared
    private let userDefaults = UserDefaults.standard

    // UserDefaults keys
    private let chatSettingsKey = "chatSettings"
    private let appSettingsKey = "appSettings"

    private init() {
        // Load settings from UserDefaults
        self.chatSettings = Self.loadChatSettings()
        self.appSettings = Self.loadAppSettings()
    }

    // MARK: - Saved Queries

    func loadSavedQueries() async {
        isLoading = true
        defer { isLoading = false }

        do {
            savedQueries = try await service.listSavedQueries()
            error = nil
        } catch {
            self.error = "Failed to load saved queries: \(error.localizedDescription)"
        }
    }

    func createSavedQuery(name: String, query: String, tags: [String]? = nil) async {
        do {
            let created = try await service.createSavedQuery(
                name: name,
                query: query,
                tags: tags
            )
            savedQueries.append(created)
            error = nil
        } catch {
            self.error = "Failed to create: \(error.localizedDescription)"
        }
    }

    func updateSavedQuery(
        id: Int,
        name: String? = nil,
        query: String? = nil,
        tags: [String]? = nil
    ) async {
        do {
            let updated = try await service.updateSavedQuery(
                id: id,
                name: name,
                query: query,
                tags: tags
            )

            if let index = savedQueries.firstIndex(where: { $0.id == id }) {
                savedQueries[index] = updated
            }

            error = nil
        } catch {
            self.error = "Failed to update: \(error.localizedDescription)"
        }
    }

    func deleteSavedQuery(id: Int) async {
        do {
            try await service.deleteSavedQuery(id: id)
            savedQueries.removeAll { $0.id == id }
            error = nil
        } catch {
            self.error = "Failed to delete: \(error.localizedDescription)"
        }
    }

    /// Load a saved query into the DatabaseStore editor
    nonisolated func loadIntoEditor(_ savedQuery: SavedQuery) {
        Task { @MainActor in
            DatabaseStore.shared.loadEditorText(savedQuery.query, contentType: .sql)
        }
    }

    /// Find exact match for current query
    func findExactMatch(for query: String) -> SavedQuery? {
        let normalized = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return savedQueries.first { savedQuery in
            savedQuery.query.trimmingCharacters(in: .whitespacesAndNewlines) == normalized
        }
    }

    /// Get queries by tag
    func queries(byTag tag: String) -> [SavedQuery] {
        savedQueries.filter { $0.tags?.contains(tag) == true }
    }

    /// Get all unique tags
    var allTags: [String] {
        let tags = savedQueries.compactMap { $0.tags }.flatMap { $0 }
        return Array(Set(tags)).sorted()
    }

    // MARK: - Chat Settings

    func updateChatSettings(_ settings: ChatSettings) {
        chatSettings = settings
        saveChatSettings(settings)
    }

    private func saveChatSettings(_ settings: ChatSettings) {
        do {
            let encoded = try JSONEncoder().encode(settings)
            userDefaults.set(encoded, forKey: chatSettingsKey)
        } catch {
            logger.error("Failed to save chat settings: \(error.localizedDescription)")
        }
    }

    private static func loadChatSettings() -> ChatSettings {
        guard let data = UserDefaults.standard.data(forKey: "chatSettings"),
              let settings = try? JSONDecoder().decode(ChatSettings.self, from: data) else {
            return .default
        }
        return settings
    }

    // MARK: - App Settings

    func updateAppSettings(_ settings: AppSettings) {
        appSettings = settings
        saveAppSettings(settings)
    }

    private func saveAppSettings(_ settings: AppSettings) {
        do {
            let encoded = try JSONEncoder().encode(settings)
            userDefaults.set(encoded, forKey: appSettingsKey)
        } catch {
            logger.error("Failed to save app settings: \(error.localizedDescription)")
        }
    }

    private static func loadAppSettings() -> AppSettings {
        guard let data = UserDefaults.standard.data(forKey: "appSettings"),
              let settings = try? JSONDecoder().decode(AppSettings.self, from: data) else {
            return .default
        }
        return settings
    }

    // MARK: - Reset

    func resetToDefaults() {
        chatSettings = .default
        appSettings = .default
        saveChatSettings(chatSettings)
        saveAppSettings(appSettings)
    }
}
