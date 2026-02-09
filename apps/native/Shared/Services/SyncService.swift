//
//  SyncService.swift
//  MagnetarStudio
//
//  Cloud synchronization service for MagnetarCloud
//  Handles sync operations, conflict resolution, and offline queuing
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SyncService")

// MARK: - Sync Models

enum SyncDirection: String, Codable, Sendable {
    case upload
    case download
    case bidirectional
}

enum SyncStatus: String, Codable, Sendable {
    case pending
    case inProgress = "in_progress"
    case completed
    case failed
    case conflict
}

enum ConflictResolution: String, Codable, Sendable {
    case localWins = "local_wins"
    case remoteWins = "remote_wins"
    case manual
    case merge
}

struct SyncResourceStatus: Codable, Sendable {
    let resource: String
    let lastSyncAt: String?
    let pendingChanges: Int
    let conflicts: Int
    let status: SyncStatus
}

struct SyncStatusResponse: Codable, Sendable {
    let isConnected: Bool
    let lastSyncAt: String?
    let pendingChanges: Int
    let activeConflicts: Int
    let resources: [SyncResourceStatus]
}

struct ConflictInfo: Codable, Sendable {
    let conflictId: String
    let resourceType: String
    let resourceId: String
    let localVersion: [String: AnyCodable]
    let remoteVersion: [String: AnyCodable]
    let localModifiedAt: String
    let remoteModifiedAt: String
    let detectedAt: String
}

struct SyncChange: Codable, Sendable {
    let resourceId: String
    let data: [String: AnyCodable]
    let modifiedAt: String
    let vectorClock: [String: Int]?
}

struct SyncExchangeResponse: Codable, Sendable {
    let received: Int
    let conflicts: [ConflictInfo]
    let serverChanges: [SyncChange]
}

// MARK: - Sync Errors

enum SyncError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case cloudUnavailable
    case conflict([ConflictInfo])
    case serverError(Int)
    case networkError(Error)
    case offlineMode

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid sync URL"
        case .invalidResponse:
            return "Invalid server response"
        case .unauthorized:
            return "Cloud authentication required"
        case .cloudUnavailable:
            return "Cloud service unavailable (air-gap mode enabled)"
        case .conflict(let conflicts):
            return "Sync conflicts detected: \(conflicts.count) items"
        case .serverError(let code):
            return "Server error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .offlineMode:
            return "Device is offline, changes queued for later sync"
        }
    }
}

// MARK: - SyncService

@MainActor @Observable
final class SyncService {
    static let shared = SyncService()

    private let baseURL: String
    private var syncTimer: Timer?
    private let syncQueue = DispatchQueue(label: "com.magnetar.sync", qos: .utility)

    // Observable state for UI binding
    private(set) var isConnected = false
    private(set) var lastSyncAt: Date?
    private(set) var pendingChanges = 0
    private(set) var activeConflicts = 0
    private(set) var isSyncing = false
    private(set) var lastError: SyncError?

    // Offline queue persisted to disk
    private var offlineQueue: [PendingSyncOperation] = []
    private let offlineQueueFile: URL

    private init() {
        self.baseURL = APIConfiguration.shared.cloudSyncURL

        // Setup offline queue persistence
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let magnetarDir = appSupport.appendingPathComponent("MagnetarStudio")
        do {
            try FileManager.default.createDirectory(at: magnetarDir, withIntermediateDirectories: true)
        } catch {
            logger.warning("Failed to create offline queue directory: \(error.localizedDescription)")
        }
        self.offlineQueueFile = magnetarDir.appendingPathComponent("sync_queue.json")

        loadOfflineQueue()
    }

    // MARK: - Sync Status

    /// Fetch current sync status from server
    func fetchStatus() async throws -> SyncStatusResponse {
        guard let url = URL(string: APIConfiguration.shared.cloudSyncStatusURL) else {
            throw SyncError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        addAuthHeaders(to: &request)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            try handleHTTPResponse(response)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let status = try decoder.decode(SyncStatusResponse.self, from: data)

            // Update published state
            await MainActor.run {
                self.isConnected = status.isConnected
                self.pendingChanges = status.pendingChanges
                self.activeConflicts = status.activeConflicts
                if let lastSync = status.lastSyncAt {
                    self.lastSyncAt = ISO8601DateFormatter().date(from: lastSync)
                }
            }

            return status
        } catch let error as SyncError {
            throw error
        } catch {
            throw SyncError.networkError(error)
        }
    }

    // MARK: - Vault Sync

    /// Sync vault items with cloud
    func syncVault(
        changes: [SyncChange],
        direction: SyncDirection = .bidirectional
    ) async throws -> SyncExchangeResponse {
        return try await performSync(
            resource: "vault",
            changes: changes,
            direction: direction
        )
    }

    // MARK: - File Upload (via CloudStorageService)

    /// Upload a large file to cloud storage
    /// Uses chunked transfer for files over 1MB
    func uploadFile(
        _ fileURL: URL,
        storageClass: StorageClass = .standard,
        encrypt: Bool = true,
        progressHandler: ((Double) -> Void)? = nil
    ) async throws -> UploadResult {
        return try await CloudStorageService.shared.uploadFile(
            fileURL,
            storageClass: storageClass,
            encrypt: encrypt,
            progressHandler: progressHandler
        )
    }

    /// Get download URL for a cloud file
    func getFileDownloadURL(fileId: String, expiresMinutes: Int = 60) async throws -> URL {
        return try await CloudStorageService.shared.getDownloadURL(
            fileId: fileId,
            expiresMinutes: expiresMinutes
        )
    }

    /// Delete a file from cloud storage
    func deleteCloudFile(_ fileId: String) async throws {
        try await CloudStorageService.shared.deleteFile(fileId)
    }

    /// Get list of files in cloud storage
    var cloudFiles: [CloudFile] {
        CloudStorageService.shared.files
    }

    /// Refresh cloud file list
    func refreshCloudFiles() async throws {
        try await CloudStorageService.shared.refreshFiles()
    }

    // MARK: - Workflow Sync

    /// Sync workflows with cloud
    func syncWorkflows(
        changes: [SyncChange],
        direction: SyncDirection = .bidirectional
    ) async throws -> SyncExchangeResponse {
        return try await performSync(
            resource: "workflows",
            changes: changes,
            direction: direction
        )
    }

    // MARK: - Team Sync

    /// Sync team data with cloud
    func syncTeams(
        changes: [SyncChange],
        direction: SyncDirection = .bidirectional
    ) async throws -> SyncExchangeResponse {
        return try await performSync(
            resource: "teams",
            changes: changes,
            direction: direction
        )
    }

    // MARK: - Conflict Resolution

    /// Get all active conflicts
    func getConflicts() async throws -> [ConflictInfo] {
        guard let url = URL(string: "\(baseURL)/conflicts") else {
            throw SyncError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        addAuthHeaders(to: &request)

        let (data, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        struct ConflictsResponse: Codable, Sendable {
            let conflicts: [ConflictInfo]
        }

        let result = try decoder.decode(ConflictsResponse.self, from: data)
        return result.conflicts
    }

    /// Resolve a specific conflict
    func resolveConflict(
        conflictId: String,
        resolution: ConflictResolution,
        mergedData: [String: AnyCodable]? = nil
    ) async throws {
        guard let url = URL(string: "\(baseURL)/conflicts/\(conflictId)/resolve") else {
            throw SyncError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)

        var body: [String: Any] = ["resolution": resolution.rawValue]
        if let merged = mergedData {
            body["merged_data"] = merged.mapValues { $0.value }
        }

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        // Refresh conflict count
        do { _ = try await fetchStatus() } catch { logger.warning("[Sync] Failed to refresh status: \(error)") }
    }

    // MARK: - Background Sync

    /// Start automatic background sync
    func startAutoSync(intervalSeconds: TimeInterval = 300) {
        stopAutoSync()

        syncTimer = Timer.scheduledTimer(withTimeInterval: intervalSeconds, repeats: true) { [weak self] _ in
            Task { [weak self] in
                do {
                    try await self?.triggerSync()
                } catch {
                    logger.warning("[Sync] Background sync failed: \(error.localizedDescription)")
                }
            }
        }

        // Trigger immediate sync
        Task {
            do {
                try await triggerSync()
            } catch {
                logger.warning("[Sync] Initial sync failed: \(error.localizedDescription)")
            }
        }
    }

    /// Stop automatic background sync
    func stopAutoSync() {
        syncTimer?.invalidate()
        syncTimer = nil
    }

    /// Trigger a full sync
    func triggerSync(resources: [String]? = nil, direction: SyncDirection = .bidirectional) async throws {
        guard let url = URL(string: "\(baseURL)/trigger") else {
            throw SyncError.invalidURL
        }

        await MainActor.run { self.isSyncing = true }
        defer { Task { @MainActor in self.isSyncing = false } }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)

        var body: [String: Any] = ["direction": direction.rawValue]
        if let resources = resources {
            body["resources"] = resources
        }

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        // Process any queued offline operations
        await processOfflineQueue()

        // Refresh status
        do { _ = try await fetchStatus() } catch { logger.warning("[Sync] Failed to refresh status: \(error)") }
    }

    // MARK: - Offline Queue

    struct PendingSyncOperation: Codable, Sendable {
        let id: UUID
        let resource: String
        let changes: [SyncChange]
        let direction: SyncDirection
        let queuedAt: Date
    }

    /// Queue an operation for later sync when offline
    func queueOfflineOperation(
        resource: String,
        changes: [SyncChange],
        direction: SyncDirection
    ) {
        let operation = PendingSyncOperation(
            id: UUID(),
            resource: resource,
            changes: changes,
            direction: direction,
            queuedAt: Date()
        )

        offlineQueue.append(operation)
        saveOfflineQueue()

        pendingChanges = offlineQueue.count
    }

    /// Process all queued offline operations
    func processOfflineQueue() async {
        guard !offlineQueue.isEmpty else { return }

        var remainingQueue: [PendingSyncOperation] = []

        for operation in offlineQueue {
            do {
                _ = try await performSync(
                    resource: operation.resource,
                    changes: operation.changes,
                    direction: operation.direction
                )
                // Success - don't re-queue
            } catch SyncError.networkError, SyncError.cloudUnavailable {
                // Still offline - keep in queue
                remainingQueue.append(operation)
            } catch {
                // Other error - log and discard
                logger.warning("Sync operation failed, discarding: \(error)")
            }
        }

        offlineQueue = remainingQueue
        saveOfflineQueue()

        await MainActor.run {
            self.pendingChanges = self.offlineQueue.count
        }
    }

    // MARK: - Private Helpers

    private func performSync(
        resource: String,
        changes: [SyncChange],
        direction: SyncDirection
    ) async throws -> SyncExchangeResponse {
        guard let url = URL(string: "\(baseURL)/\(resource)") else {
            throw SyncError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        struct SyncRequest: Codable, Sendable {
            let direction: SyncDirection
            let changes: [SyncChange]
        }

        let syncRequest = SyncRequest(direction: direction, changes: changes)
        request.httpBody = try encoder.encode(syncRequest)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            try handleHTTPResponse(response)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(SyncExchangeResponse.self, from: data)
        } catch {
            // Queue for later if offline
            if case SyncError.networkError = error {
                queueOfflineOperation(resource: resource, changes: changes, direction: direction)
                throw SyncError.offlineMode
            }
            throw error
        }
    }

    private func addAuthHeaders(to request: inout URLRequest) {
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add cloud session token if available
        if let cloudToken = KeychainService.shared.loadToken(forKey: "cloud_access_token") {
            request.setValue("Bearer \(cloudToken)", forHTTPHeaderField: "X-Cloud-Token")
        }
    }

    private func handleHTTPResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw SyncError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return // Success
        case 401, 403:
            throw SyncError.unauthorized
        case 503:
            throw SyncError.cloudUnavailable
        default:
            throw SyncError.serverError(httpResponse.statusCode)
        }
    }

    private func loadOfflineQueue() {
        guard FileManager.default.fileExists(atPath: offlineQueueFile.path) else { return }

        do {
            let data = try Data(contentsOf: offlineQueueFile)
            offlineQueue = try JSONDecoder().decode([PendingSyncOperation].self, from: data)
            pendingChanges = offlineQueue.count
        } catch {
            logger.warning("Failed to load offline sync queue: \(error)")
        }
    }

    private func saveOfflineQueue() {
        let queue = offlineQueue
        let file = offlineQueueFile
        syncQueue.async {
            do {
                let data = try JSONEncoder().encode(queue)
                try data.write(to: file, options: .atomic)
            } catch {
                logger.warning("Failed to save offline sync queue: \(error)")
            }
        }
    }
}

// Note: AnyCodable is defined in Shared/Models/AnyCodable.swift
