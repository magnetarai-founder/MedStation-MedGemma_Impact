//
//  TeamStore.swift
//  MagnetarStudio
//
//  SPDX-License-Identifier: Proprietary
//

import Foundation
import Observation

// MARK: - TeamStore

/// Central state management for the Team collaboration workspace.
///
/// ## Overview
/// TeamStore manages team membership, channels, and messaging. Supports public channels,
/// private channels, and direct messages. Includes client-side unread tracking.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `TeamStore.shared`
///
/// ## State Persistence (UserDefaults)
/// - `selectedTeamId` - Last selected team
/// - `selectedChannelId` - Last viewed channel
/// - `lastRead.<channelId>` - Last read message ID per channel (for unread counts)
///
/// ## Channel Types
/// - `public` - Open to all team members
/// - `private` - Invite-only channels
/// - `direct` - 1:1 direct messages
///
/// ## Unread Tracking
/// Client-side tracking via UserDefaults:
/// - `markChannelAsRead()` - Mark channel as read up to latest message
/// - `unreadCount(forChannelId:)` - Count messages after last read position
///
/// ## Dependencies
/// - `TeamService` - Backend team/channel/message API
///
/// ## Usage
/// ```swift
/// let store = TeamStore.shared
///
/// // Load teams and channels
/// await store.loadTeams()
/// await store.loadChannels()
///
/// // Load messages for a channel
/// await store.loadMessages(channelId: "general")
///
/// // Send message
/// await store.sendMessage(channelId: "general", content: "Hello team!")
///
/// // Check unread count
/// let unread = store.unreadCount(forChannelId: "general")
/// ```
@MainActor
@Observable
final class TeamStore {
    static let shared = TeamStore()

    // MARK: - State Persistence Keys
    private static let selectedTeamIdKey = "team.selectedTeamId"
    private static let selectedChannelIdKey = "team.selectedChannelId"

    // MARK: - Observable State

    var teams: [Team] = []
    var channels: [TeamChannel] = []
    var messages: [TeamMessage] = []
    var selectedTeamId: String? {
        didSet { UserDefaults.standard.set(selectedTeamId, forKey: Self.selectedTeamIdKey) }
    }
    var selectedChannelId: String? {
        didSet { UserDefaults.standard.set(selectedChannelId, forKey: Self.selectedChannelIdKey) }
    }
    var isLoading = false
    var error: String?

    private let service = TeamService.shared

    // Client-side unread tracking (until backend support added)
    private static let lastReadPrefix = "team.lastRead."

    private init() {
        // Restore persisted state
        self.selectedTeamId = UserDefaults.standard.string(forKey: Self.selectedTeamIdKey)
        self.selectedChannelId = UserDefaults.standard.string(forKey: Self.selectedChannelIdKey)
    }

    // MARK: - Unread Tracking

    /// Get the last read message ID for a channel
    private func lastReadMessageId(forChannelId channelId: String) -> String? {
        UserDefaults.standard.string(forKey: Self.lastReadPrefix + channelId)
    }

    /// Mark a channel as read up to the latest message
    func markChannelAsRead(_ channelId: String) {
        guard let latestMessage = messages.last else { return }
        UserDefaults.standard.set(latestMessage.id, forKey: Self.lastReadPrefix + channelId)
    }

    // MARK: - Team Management

    func loadTeams() async {
        isLoading = true
        defer { isLoading = false }

        do {
            teams = try await service.listTeams()
            error = nil
        } catch {
            self.error = "Failed to load teams: \(error.localizedDescription)"
        }
    }

    func createTeam(name: String, description: String?) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newTeam = try await service.createTeam(name: name, description: description)
            teams.insert(newTeam, at: 0)
            error = nil
        } catch {
            self.error = "Failed to create team: \(error.localizedDescription)"
        }
    }

    func joinTeam(code: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let team = try await service.joinTeam(code: code)
            if !teams.contains(where: { $0.id == team.id }) {
                teams.insert(team, at: 0)
            }
            error = nil
        } catch {
            self.error = "Failed to join team: \(error.localizedDescription)"
        }
    }

    // MARK: - Channel Management

    func loadChannels() async {
        isLoading = true
        defer { isLoading = false }

        do {
            channels = try await service.listChannels()
            error = nil
        } catch {
            self.error = "Failed to load channels: \(error.localizedDescription)"
        }
    }

    // MARK: - Message Management

    func loadMessages(channelId: String, limit: Int = 50) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let response = try await service.getMessages(channelId: channelId, limit: limit)
            messages = response.messages
            selectedChannelId = channelId
            error = nil
        } catch {
            self.error = "Failed to load messages: \(error.localizedDescription)"
        }
    }

    func sendMessage(channelId: String, content: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newMessage = try await service.sendMessage(channelId: channelId, content: content)
            messages.append(newMessage)
            error = nil
        } catch {
            self.error = "Failed to send message: \(error.localizedDescription)"
        }
    }

    // MARK: - Helpers

    /// Get channels grouped by type
    func channelsByType() -> [String: [TeamChannel]] {
        Dictionary(grouping: channels) { $0.type }
    }

    /// Get public channels
    var publicChannels: [TeamChannel] {
        channels.filter { $0.type == "public" }
    }

    /// Get private channels
    var privateChannels: [TeamChannel] {
        channels.filter { $0.type == "private" }
    }

    /// Get direct message channels
    var directMessages: [TeamChannel] {
        channels.filter { $0.type == "direct" }
    }

    /// Get recent messages (last N)
    func recentMessages(limit: Int = 10) -> [TeamMessage] {
        Array(messages.suffix(limit))
    }

    /// Get unread message count for a channel
    /// Uses client-side tracking - counts messages after last read message ID
    func unreadCount(forChannelId channelId: String) -> Int {
        guard let lastReadId = lastReadMessageId(forChannelId: channelId) else {
            // Never read this channel - all messages are unread
            return messages.filter { $0.channelId == channelId }.count
        }

        // Find index of last read message
        guard let lastReadIndex = messages.firstIndex(where: { $0.id == lastReadId }) else {
            // Last read message no longer in memory - count all as unread
            return messages.filter { $0.channelId == channelId }.count
        }

        // Count messages after the last read one
        return messages.suffix(from: lastReadIndex + 1)
            .filter { $0.channelId == channelId }
            .count
    }

    /// Get channel by ID
    func channel(withId id: String) -> TeamChannel? {
        channels.first { $0.id == id }
    }
}
