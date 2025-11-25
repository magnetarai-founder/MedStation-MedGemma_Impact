import Foundation
import Combine

/// Settings store for saved queries and app preferences
@MainActor
final class SettingsStore: ObservableObject {
    static let shared = SettingsStore()

    // MARK: - Published State

    @Published var savedQueries: [SavedQuery] = []
    @Published var chatSettings: ChatSettings
    @Published var appSettings: AppSettings
    @Published var isLoading = false
    @Published var error: String?

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
    func loadIntoEditor(_ savedQuery: SavedQuery, databaseStore: DatabaseStore = .shared) {
        databaseStore.loadEditorText(savedQuery.query, contentType: .sql)
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
        if let encoded = try? JSONEncoder().encode(settings) {
            userDefaults.set(encoded, forKey: chatSettingsKey)
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
        if let encoded = try? JSONEncoder().encode(settings) {
            userDefaults.set(encoded, forKey: appSettingsKey)
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
