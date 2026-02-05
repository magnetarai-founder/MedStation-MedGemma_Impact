//
//  UserBehaviorTracker.swift
//  MagnetarStudio
//
//  Tracks user behavior patterns for ANE-powered predictions.
//  Ported from MagnetarAI-iPad with MagnetarStudio-specific events.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "UserBehaviorTracker")

// MARK: - User Behavior Tracker

@MainActor
final class UserBehaviorTracker: ObservableObject {

    // MARK: - Published State

    @Published private(set) var currentPatterns: UserBehaviorPatterns = UserBehaviorPatterns()
    @Published private(set) var isTracking: Bool = true

    // MARK: - Storage

    private let storageURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    // MARK: - Event Buffer

    private var eventBuffer: [BehaviorEvent] = []
    private let maxBufferSize = 100
    private var lastFlushTime = Date()
    private let flushInterval: TimeInterval = 60  // Flush every minute

    // MARK: - Singleton

    static let shared = UserBehaviorTracker()

    // MARK: - Initialization

    init() {
        let documentsPath = (FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
        self.storageURL = documentsPath.appendingPathComponent(".magnetar_studio/user_model/behavior_patterns.json")

        encoder.outputFormatting = .prettyPrinted
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        loadPatterns()
        logger.info("[BehaviorTracker] Initialized with \(self.currentPatterns.totalEvents) tracked events")
    }

    // MARK: - Event Recording

    /// Record a behavior event
    func record(_ eventType: BehaviorEventType, metadata: [String: String] = [:]) {
        guard isTracking else { return }

        let event = BehaviorEvent(
            type: eventType,
            timestamp: Date(),
            metadata: metadata
        )

        eventBuffer.append(event)

        // Update patterns in real-time
        updatePatterns(with: event)

        // Flush if buffer is full or interval elapsed
        if eventBuffer.count >= maxBufferSize ||
           Date().timeIntervalSince(lastFlushTime) >= flushInterval {
            flush()
        }

        logger.debug("[BehaviorTracker] Recorded: \(eventType.rawValue)")
    }

    // MARK: - Convenience Recording Methods

    func trackMessageSent(sessionId: UUID, modelId: String?) {
        record(.messageSent, metadata: [
            "session_id": sessionId.uuidString,
            "model_id": modelId ?? "unknown"
        ])
    }

    func trackFileUploaded(fileType: String, sessionId: UUID) {
        record(.fileUploaded, metadata: [
            "file_type": fileType,
            "session_id": sessionId.uuidString
        ])
    }

    func trackTabSwitched(from: String, to: String) {
        record(.tabSwitched, metadata: [
            "from_tab": from,
            "to_tab": to
        ])
    }

    func trackWorkflowExecuted(workflowId: UUID) {
        record(.workflowExecuted, metadata: [
            "workflow_id": workflowId.uuidString
        ])
    }

    func trackKanbanTaskCreated(taskId: UUID, projectId: UUID) {
        record(.kanbanTaskCreated, metadata: [
            "task_id": taskId.uuidString,
            "project_id": projectId.uuidString
        ])
    }

    func trackVaultFileAccessed(fileId: UUID) {
        record(.vaultFileAccessed, metadata: [
            "file_id": fileId.uuidString
        ])
    }

    func trackCodeFileEdited(filePath: String) {
        record(.codeFileEdited, metadata: [
            "file_path": filePath
        ])
    }

    func trackModelSwitched(from: String?, to: String) {
        record(.modelSwitched, metadata: [
            "from_model": from ?? "none",
            "to_model": to
        ])
    }

    func trackP2PPeerConnected(peerId: String) {
        record(.p2pPeerConnected, metadata: [
            "peer_id": peerId
        ])
    }

    func trackSessionCompacted(sessionId: UUID, tokensSaved: Int) {
        record(.sessionCompacted, metadata: [
            "session_id": sessionId.uuidString,
            "tokens_saved": String(tokensSaved)
        ])
    }

    // MARK: - Pattern Updates

    private func updatePatterns(with event: BehaviorEvent) {
        currentPatterns.totalEvents += 1
        currentPatterns.lastEventAt = event.timestamp

        // Update time-of-day patterns
        let hour = Calendar.current.component(.hour, from: event.timestamp)
        currentPatterns.hourlyActivity[hour, default: 0] += 1

        // Update day-of-week patterns
        let weekday = Calendar.current.component(.weekday, from: event.timestamp)
        currentPatterns.weekdayActivity[weekday, default: 0] += 1

        // Update event type counts
        currentPatterns.eventTypeCounts[event.type.rawValue, default: 0] += 1

        // Update recent topics (from metadata)
        if let topic = event.metadata["topic"] {
            currentPatterns.recentTopics.insert(topic, at: 0)
            if currentPatterns.recentTopics.count > 20 {
                currentPatterns.recentTopics.removeLast()
            }
        }

        // Update file type affinities
        if event.type == .fileUploaded || event.type == .vaultFileAccessed,
           let fileType = event.metadata["file_type"] {
            currentPatterns.fileTypeAffinities[fileType, default: 0] += 1
        }

        // Update workspace transition patterns
        if event.type == .tabSwitched,
           let from = event.metadata["from_tab"],
           let to = event.metadata["to_tab"] {
            let key = "\(from)->\(to)"
            currentPatterns.workspaceTransitions[key, default: 0] += 1
        }
    }

    // MARK: - Pattern Analysis

    /// Get peak activity hours
    func peakActivityHours(count: Int = 3) -> [Int] {
        return currentPatterns.hourlyActivity
            .sorted { $0.value > $1.value }
            .prefix(count)
            .map { $0.key }
    }

    /// Get most common file types
    func preferredFileTypes(count: Int = 5) -> [String] {
        return currentPatterns.fileTypeAffinities
            .sorted { $0.value > $1.value }
            .prefix(count)
            .map { $0.key }
    }

    /// Get most common workspace transitions
    func commonTransitions(count: Int = 5) -> [(from: String, to: String, count: Int)] {
        return currentPatterns.workspaceTransitions
            .sorted { $0.value > $1.value }
            .prefix(count)
            .compactMap { key, value -> (String, String, Int)? in
                let parts = key.split(separator: ">")
                guard parts.count == 2 else { return nil }
                let from = String(parts[0]).replacingOccurrences(of: "-", with: "")
                let to = String(parts[1])
                return (from, to, value)
            }
    }

    /// Check if current time is a peak activity time
    func isCurrentlyPeakTime() -> Bool {
        let currentHour = Calendar.current.component(.hour, from: Date())
        let peakHours = peakActivityHours(count: 5)
        return peakHours.contains(currentHour)
    }

    // MARK: - Persistence

    func flush() {
        savePatterns()
        eventBuffer.removeAll()
        lastFlushTime = Date()
    }

    private func savePatterns() {
        do {
            // Ensure directory exists
            let directory = storageURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

            let data = try encoder.encode(currentPatterns)
            try data.write(to: storageURL)
            logger.debug("[BehaviorTracker] Saved patterns")
        } catch {
            logger.error("[BehaviorTracker] Failed to save: \(error)")
        }
    }

    private func loadPatterns() {
        guard let data = try? Data(contentsOf: storageURL) else {
            logger.info("[BehaviorTracker] No existing patterns, starting fresh")
            return
        }
        do {
            currentPatterns = try decoder.decode(UserBehaviorPatterns.self, from: data)
        } catch {
            logger.warning("[BehaviorTracker] Failed to decode patterns: \(error)")
        }
    }

    /// Reset all tracked patterns
    func reset() {
        currentPatterns = UserBehaviorPatterns()
        eventBuffer.removeAll()
        try? FileManager.default.removeItem(at: storageURL)
        logger.info("[BehaviorTracker] Reset all patterns")
    }

    /// Enable/disable tracking
    func setTracking(enabled: Bool) {
        isTracking = enabled
        logger.info("[BehaviorTracker] Tracking \(enabled ? "enabled" : "disabled")")
    }
}

// MARK: - Behavior Event Type

enum BehaviorEventType: String, Codable, CaseIterable, Sendable {
    // Core events (from iPad)
    case messageSent = "message_sent"
    case fileUploaded = "file_uploaded"
    case fileAccessed = "file_accessed"
    case tabSwitched = "tab_switched"
    case sessionCreated = "session_created"
    case sessionCompacted = "session_compacted"
    case themeAccessed = "theme_accessed"
    case searchPerformed = "search_performed"

    // MagnetarStudio-specific events
    case workflowExecuted = "workflow_executed"
    case kanbanTaskCreated = "kanban_task_created"
    case vaultFileAccessed = "vault_file_accessed"
    case teamMessageSent = "team_message_sent"
    case codeFileEdited = "code_file_edited"
    case p2pPeerConnected = "p2p_peer_connected"
    case modelSwitched = "model_switched"
    case huggingFaceModelDownloaded = "huggingface_model_downloaded"

    var category: EventCategory {
        switch self {
        case .messageSent, .sessionCreated, .sessionCompacted, .themeAccessed:
            return .chat
        case .fileUploaded, .fileAccessed, .vaultFileAccessed:
            return .files
        case .tabSwitched:
            return .navigation
        case .searchPerformed:
            return .search
        case .workflowExecuted:
            return .workflow
        case .kanbanTaskCreated:
            return .kanban
        case .teamMessageSent, .p2pPeerConnected:
            return .collaboration
        case .codeFileEdited:
            return .code
        case .modelSwitched, .huggingFaceModelDownloaded:
            return .models
        }
    }

    enum EventCategory: String, Codable, Sendable {
        case chat
        case files
        case navigation
        case search
        case workflow
        case kanban
        case collaboration
        case code
        case models
    }
}

// MARK: - Behavior Event

struct BehaviorEvent: Codable, Identifiable, Sendable {
    let id: UUID
    let type: BehaviorEventType
    let timestamp: Date
    let metadata: [String: String]

    init(
        id: UUID = UUID(),
        type: BehaviorEventType,
        timestamp: Date = Date(),
        metadata: [String: String] = [:]
    ) {
        self.id = id
        self.type = type
        self.timestamp = timestamp
        self.metadata = metadata
    }
}

// MARK: - User Behavior Patterns

struct UserBehaviorPatterns: Codable, Sendable {
    var totalEvents: Int = 0
    var lastEventAt: Date?

    /// Activity count per hour (0-23)
    var hourlyActivity: [Int: Int] = [:]

    /// Activity count per weekday (1=Sunday, 7=Saturday)
    var weekdayActivity: [Int: Int] = [:]

    /// Count per event type
    var eventTypeCounts: [String: Int] = [:]

    /// Recent topics discussed
    var recentTopics: [String] = []

    /// File type usage counts
    var fileTypeAffinities: [String: Int] = [:]

    /// Workspace transition counts ("chat->data": 5)
    var workspaceTransitions: [String: Int] = [:]

    /// Model usage counts
    var modelUsageCounts: [String: Int] = [:]

    /// Average session length in messages
    var averageSessionLength: Double = 0

    /// Compaction frequency (compactions per 100 messages)
    var compactionFrequency: Double = 0
}
