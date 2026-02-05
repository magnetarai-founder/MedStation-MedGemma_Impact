//
//  CodingConversationStorage.swift
//  MagnetarStudio
//
//  Specialized conversation storage for the Coding workspace.
//  Extends ConversationStorageService with JSONL message logging,
//  terminal context persistence, and session branching support.
//
//  Storage Structure:
//  .magnetar_studio/coding_sessions/
//  ├── session_[uuid]/
//  │   ├── metadata.json
//  │   ├── messages.jsonl        (append-only message log)
//  │   ├── terminal_contexts.jsonl
//  │   ├── branches/
//  │   │   └── branch_[uuid].json
//  │   └── themes/
//  │       └── theme_[uuid].json
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodingConversationStorage")

// MARK: - Coding Session Models

/// Metadata for a coding session
struct CodingSessionMetadata: Codable, Identifiable, Sendable {
    let id: UUID
    var title: String
    var workspacePath: String?
    var preferredTerminal: String?
    var preferredModel: String?
    var messageCount: Int
    var terminalContextCount: Int
    var createdAt: Date
    var updatedAt: Date
    var activeBranchId: UUID?
    var primaryTopics: [String]

    init(
        id: UUID = UUID(),
        title: String = "New Coding Session",
        workspacePath: String? = nil,
        preferredTerminal: String? = nil,
        preferredModel: String? = nil,
        messageCount: Int = 0,
        terminalContextCount: Int = 0,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        activeBranchId: UUID? = nil,
        primaryTopics: [String] = []
    ) {
        self.id = id
        self.title = title
        self.workspacePath = workspacePath
        self.preferredTerminal = preferredTerminal
        self.preferredModel = preferredModel
        self.messageCount = messageCount
        self.terminalContextCount = terminalContextCount
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.activeBranchId = activeBranchId
        self.primaryTopics = primaryTopics
    }
}

/// A message entry in the JSONL log
struct CodingMessageEntry: Codable, Identifiable, Sendable {
    let id: UUID
    let role: String  // "user", "assistant", "system"
    let content: String
    let timestamp: Date
    let branchId: UUID?
    let terminalContextId: UUID?
    let modelId: String?

    /// Additional metadata
    var metadata: [String: String]?

    init(
        id: UUID = UUID(),
        role: String,
        content: String,
        timestamp: Date = Date(),
        branchId: UUID? = nil,
        terminalContextId: UUID? = nil,
        modelId: String? = nil,
        metadata: [String: String]? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.branchId = branchId
        self.terminalContextId = terminalContextId
        self.modelId = modelId
        self.metadata = metadata
    }
}

/// Terminal context entry for JSONL log
struct TerminalContextEntry: Codable, Identifiable, Sendable {
    let id: UUID
    let command: String
    let output: String
    let exitCode: Int
    let workingDirectory: String
    let timestamp: Date
    let branchId: UUID?
    let parsedErrors: [ParsedErrorEntry]?

    struct ParsedErrorEntry: Codable, Sendable {
        let category: String
        let summary: String
        let severity: String
    }

    init(
        id: UUID = UUID(),
        command: String,
        output: String,
        exitCode: Int,
        workingDirectory: String,
        timestamp: Date = Date(),
        branchId: UUID? = nil,
        parsedErrors: [ParsedErrorEntry]? = nil
    ) {
        self.id = id
        self.command = command
        self.output = output
        self.exitCode = exitCode
        self.workingDirectory = workingDirectory
        self.timestamp = timestamp
        self.branchId = branchId
        self.parsedErrors = parsedErrors
    }

    /// Create from TerminalContext
    init(from context: TerminalContext, branchId: UUID? = nil, parsedErrors: [ParsedTerminalError]? = nil) {
        self.id = UUID()
        self.command = context.command
        self.output = context.output
        self.exitCode = context.exitCode
        self.workingDirectory = context.workingDirectory
        self.timestamp = context.timestamp
        self.branchId = branchId
        self.parsedErrors = parsedErrors?.map { error in
            ParsedErrorEntry(
                category: error.category.rawValue,
                summary: error.summary,
                severity: error.severity.rawValue
            )
        }
    }
}

/// Branch metadata
struct CodingSessionBranch: Codable, Identifiable, Sendable {
    let id: UUID
    let parentBranchId: UUID?
    var name: String
    var topic: String?
    let createdAt: Date
    var messageCount: Int
    var isActive: Bool
    var isMerged: Bool
    var mergedIntoId: UUID?

    /// Context snapshot at branch point
    var contextSnapshot: BranchContextSnapshot?

    struct BranchContextSnapshot: Codable, Sendable {
        let lastMessageId: UUID?
        let messageCount: Int
        let timestamp: Date
        let summary: String?
    }

    init(
        id: UUID = UUID(),
        parentBranchId: UUID? = nil,
        name: String,
        topic: String? = nil,
        createdAt: Date = Date(),
        messageCount: Int = 0,
        isActive: Bool = true,
        isMerged: Bool = false,
        mergedIntoId: UUID? = nil,
        contextSnapshot: BranchContextSnapshot? = nil
    ) {
        self.id = id
        self.parentBranchId = parentBranchId
        self.name = name
        self.topic = topic
        self.createdAt = createdAt
        self.messageCount = messageCount
        self.isActive = isActive
        self.isMerged = isMerged
        self.mergedIntoId = mergedIntoId
        self.contextSnapshot = contextSnapshot
    }
}

// MARK: - Coding Conversation Storage Service

/// Service for persisting coding workspace conversations with JSONL logging
@MainActor
final class CodingConversationStorage {
    // MARK: - Singleton

    static let shared = CodingConversationStorage()

    // MARK: - Properties

    private let fileManager = FileManager.default
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    /// Root directory for coding sessions
    private let rootDirectory: URL

    /// Currently active session ID
    private(set) var activeSessionId: UUID?

    // MARK: - Init

    init() {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.rootDirectory = documentsPath
            .appendingPathComponent(".magnetar_studio", isDirectory: true)
            .appendingPathComponent("coding_sessions", isDirectory: true)

        encoder.outputFormatting = [.sortedKeys]  // Compact for JSONL
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        setupDirectoryStructure()
        logger.info("[CodingStorage] Initialized at \(self.rootDirectory.path)")
    }

    // MARK: - Directory Setup

    private func setupDirectoryStructure() {
        try? fileManager.createDirectory(at: rootDirectory, withIntermediateDirectories: true)
    }

    private func sessionDirectory(_ id: UUID) -> URL {
        rootDirectory.appendingPathComponent("session_\(id.uuidString)")
    }

    private func ensureSessionDirectory(_ id: UUID) {
        let sessionDir = sessionDirectory(id)
        let subdirs = ["branches", "themes"]

        try? fileManager.createDirectory(at: sessionDir, withIntermediateDirectories: true)
        for subdir in subdirs {
            let path = sessionDir.appendingPathComponent(subdir)
            try? fileManager.createDirectory(at: path, withIntermediateDirectories: true)
        }
    }

    // MARK: - Session Management

    /// Create a new coding session
    func createSession(
        title: String = "New Coding Session",
        workspacePath: String? = nil,
        preferredTerminal: String? = nil
    ) throws -> CodingSessionMetadata {
        let metadata = CodingSessionMetadata(
            title: title,
            workspacePath: workspacePath,
            preferredTerminal: preferredTerminal
        )

        ensureSessionDirectory(metadata.id)
        try saveMetadata(metadata)

        // Create main branch
        let mainBranch = CodingSessionBranch(name: "main")
        try saveBranch(mainBranch, for: metadata.id)

        activeSessionId = metadata.id
        logger.info("[CodingStorage] Created session: \(metadata.id)")

        return metadata
    }

    /// List all coding sessions
    func listSessions() -> [CodingSessionMetadata] {
        guard let contents = try? fileManager.contentsOfDirectory(
            at: rootDirectory,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return contents.compactMap { url -> CodingSessionMetadata? in
            guard url.lastPathComponent.hasPrefix("session_") else { return nil }
            let metadataUrl = url.appendingPathComponent("metadata.json")
            guard let data = try? Data(contentsOf: metadataUrl) else { return nil }
            return try? decoder.decode(CodingSessionMetadata.self, from: data)
        }
        .sorted { $0.updatedAt > $1.updatedAt }
    }

    /// Load a session by ID
    func loadSession(_ id: UUID) throws -> CodingSessionMetadata {
        let url = sessionDirectory(id).appendingPathComponent("metadata.json")
        let data = try Data(contentsOf: url)
        return try decoder.decode(CodingSessionMetadata.self, from: data)
    }

    /// Save session metadata
    func saveMetadata(_ metadata: CodingSessionMetadata) throws {
        ensureSessionDirectory(metadata.id)
        let url = sessionDirectory(metadata.id).appendingPathComponent("metadata.json")

        // Use pretty printing for metadata
        let prettyEncoder = JSONEncoder()
        prettyEncoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        prettyEncoder.dateEncodingStrategy = .iso8601

        let data = try prettyEncoder.encode(metadata)
        try data.write(to: url)
    }

    /// Delete a session
    func deleteSession(_ id: UUID) throws {
        let url = sessionDirectory(id)
        try fileManager.removeItem(at: url)
        if activeSessionId == id {
            activeSessionId = nil
        }
        logger.info("[CodingStorage] Deleted session: \(id)")
    }

    // MARK: - JSONL Message Logging

    /// Append a message to the session log (JSONL format)
    func appendMessage(_ message: CodingMessageEntry, to sessionId: UUID) throws {
        let url = sessionDirectory(sessionId).appendingPathComponent("messages.jsonl")
        let data = try encoder.encode(message)

        guard var jsonString = String(data: data, encoding: .utf8) else {
            throw CodingStorageError.encodingFailed
        }

        // Ensure single line (remove any newlines in content)
        jsonString = jsonString.replacingOccurrences(of: "\n", with: "\\n")
        jsonString += "\n"

        guard let lineData = jsonString.data(using: .utf8) else {
            throw CodingStorageError.encodingFailed
        }

        if fileManager.fileExists(atPath: url.path) {
            // Append to existing file
            let fileHandle = try FileHandle(forWritingTo: url)
            defer { try? fileHandle.close() }
            fileHandle.seekToEndOfFile()
            fileHandle.write(lineData)
        } else {
            // Create new file
            try jsonString.write(to: url, atomically: true, encoding: .utf8)
        }

        // Update metadata
        var metadata = try loadSession(sessionId)
        metadata.messageCount += 1
        metadata.updatedAt = Date()
        try saveMetadata(metadata)

        logger.debug("[CodingStorage] Appended message to session \(sessionId)")
    }

    /// Load all messages for a session
    func loadMessages(for sessionId: UUID, limit: Int? = nil, offset: Int = 0) throws -> [CodingMessageEntry] {
        let url = sessionDirectory(sessionId).appendingPathComponent("messages.jsonl")

        guard fileManager.fileExists(atPath: url.path) else {
            return []
        }

        let content = try String(contentsOf: url, encoding: .utf8)
        let lines = content.components(separatedBy: "\n").filter { !$0.isEmpty }

        var messages: [CodingMessageEntry] = []
        let startIndex = offset
        let endIndex = limit.map { min(startIndex + $0, lines.count) } ?? lines.count

        for i in startIndex..<endIndex {
            guard i < lines.count else { break }
            // Unescape newlines for parsing
            let line = lines[i].replacingOccurrences(of: "\\n", with: "\n")
            if let data = line.data(using: .utf8),
               let message = try? decoder.decode(CodingMessageEntry.self, from: data) {
                messages.append(message)
            }
        }

        return messages
    }

    /// Load messages for a specific branch
    func loadMessages(for sessionId: UUID, branchId: UUID) throws -> [CodingMessageEntry] {
        let allMessages = try loadMessages(for: sessionId)
        return allMessages.filter { $0.branchId == branchId || $0.branchId == nil }
    }

    // MARK: - Terminal Context Logging

    /// Append terminal context to the session log
    func appendTerminalContext(_ context: TerminalContextEntry, to sessionId: UUID) throws {
        let url = sessionDirectory(sessionId).appendingPathComponent("terminal_contexts.jsonl")
        let data = try encoder.encode(context)

        guard var jsonString = String(data: data, encoding: .utf8) else {
            throw CodingStorageError.encodingFailed
        }

        jsonString = jsonString.replacingOccurrences(of: "\n", with: "\\n")
        jsonString += "\n"

        guard let lineData = jsonString.data(using: .utf8) else {
            throw CodingStorageError.encodingFailed
        }

        if fileManager.fileExists(atPath: url.path) {
            let fileHandle = try FileHandle(forWritingTo: url)
            defer { try? fileHandle.close() }
            fileHandle.seekToEndOfFile()
            fileHandle.write(lineData)
        } else {
            try jsonString.write(to: url, atomically: true, encoding: .utf8)
        }

        // Update metadata
        var metadata = try loadSession(sessionId)
        metadata.terminalContextCount += 1
        metadata.updatedAt = Date()
        try saveMetadata(metadata)
    }

    /// Load terminal contexts for a session
    func loadTerminalContexts(for sessionId: UUID, limit: Int? = nil) throws -> [TerminalContextEntry] {
        let url = sessionDirectory(sessionId).appendingPathComponent("terminal_contexts.jsonl")

        guard fileManager.fileExists(atPath: url.path) else {
            return []
        }

        let content = try String(contentsOf: url, encoding: .utf8)
        let lines = content.components(separatedBy: "\n").filter { !$0.isEmpty }

        var contexts: [TerminalContextEntry] = []
        let linesToProcess = limit.map { Array(lines.suffix($0)) } ?? lines

        for line in linesToProcess {
            let unescaped = line.replacingOccurrences(of: "\\n", with: "\n")
            if let data = unescaped.data(using: .utf8),
               let context = try? decoder.decode(TerminalContextEntry.self, from: data) {
                contexts.append(context)
            }
        }

        return contexts
    }

    // MARK: - Branch Management

    /// Save a branch
    func saveBranch(_ branch: CodingSessionBranch, for sessionId: UUID) throws {
        let url = sessionDirectory(sessionId)
            .appendingPathComponent("branches")
            .appendingPathComponent("branch_\(branch.id.uuidString).json")

        let prettyEncoder = JSONEncoder()
        prettyEncoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        prettyEncoder.dateEncodingStrategy = .iso8601

        let data = try prettyEncoder.encode(branch)
        try data.write(to: url)
    }

    /// Load all branches for a session
    func loadBranches(for sessionId: UUID) throws -> [CodingSessionBranch] {
        let branchesDir = sessionDirectory(sessionId).appendingPathComponent("branches")

        guard let contents = try? fileManager.contentsOfDirectory(
            at: branchesDir,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return contents.compactMap { url -> CodingSessionBranch? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(CodingSessionBranch.self, from: data)
        }
        .sorted { $0.createdAt < $1.createdAt }
    }

    /// Create a new branch from current state
    func createBranch(
        name: String,
        topic: String? = nil,
        for sessionId: UUID,
        parentBranchId: UUID? = nil
    ) throws -> CodingSessionBranch {
        let metadata = try loadSession(sessionId)
        let messages = try loadMessages(for: sessionId)

        let snapshot = CodingSessionBranch.BranchContextSnapshot(
            lastMessageId: messages.last?.id,
            messageCount: messages.count,
            timestamp: Date(),
            summary: nil
        )

        let branch = CodingSessionBranch(
            parentBranchId: parentBranchId,
            name: name,
            topic: topic,
            contextSnapshot: snapshot
        )

        try saveBranch(branch, for: sessionId)

        // Update metadata with active branch
        var updatedMetadata = metadata
        updatedMetadata.activeBranchId = branch.id
        updatedMetadata.updatedAt = Date()
        try saveMetadata(updatedMetadata)

        logger.info("[CodingStorage] Created branch '\(name)' for session \(sessionId)")
        return branch
    }

    /// Switch to a different branch
    func switchBranch(to branchId: UUID, for sessionId: UUID) throws {
        var metadata = try loadSession(sessionId)
        metadata.activeBranchId = branchId
        metadata.updatedAt = Date()
        try saveMetadata(metadata)

        logger.info("[CodingStorage] Switched to branch \(branchId)")
    }

    // MARK: - Theme Integration

    /// Save a theme for a session
    func saveTheme(_ theme: ConversationTheme, for sessionId: UUID) throws {
        let url = sessionDirectory(sessionId)
            .appendingPathComponent("themes")
            .appendingPathComponent("theme_\(theme.id.uuidString).json")

        let prettyEncoder = JSONEncoder()
        prettyEncoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        prettyEncoder.dateEncodingStrategy = .iso8601

        let data = try prettyEncoder.encode(theme)
        try data.write(to: url)
    }

    /// Load themes for a session
    func loadThemes(for sessionId: UUID) throws -> [ConversationTheme] {
        let themesDir = sessionDirectory(sessionId).appendingPathComponent("themes")

        guard let contents = try? fileManager.contentsOfDirectory(
            at: themesDir,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return contents.compactMap { url -> ConversationTheme? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(ConversationTheme.self, from: data)
        }
        .sorted { $0.createdAt < $1.createdAt }
    }

    // MARK: - Storage Info

    /// Get storage size for a session
    func getStorageSize(for sessionId: UUID) -> Int64 {
        let sessionDir = sessionDirectory(sessionId)
        return directorySize(at: sessionDir)
    }

    /// Get total storage size
    func getTotalStorageSize() -> Int64 {
        return directorySize(at: rootDirectory)
    }

    private func directorySize(at url: URL) -> Int64 {
        guard let enumerator = fileManager.enumerator(
            at: url,
            includingPropertiesForKeys: [.fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return 0
        }

        var totalSize: Int64 = 0
        for case let fileURL as URL in enumerator {
            if let size = try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize {
                totalSize += Int64(size)
            }
        }
        return totalSize
    }
}

// MARK: - Errors

enum CodingStorageError: LocalizedError {
    case sessionNotFound
    case encodingFailed
    case decodingFailed
    case branchNotFound

    var errorDescription: String? {
        switch self {
        case .sessionNotFound:
            return "Coding session not found"
        case .encodingFailed:
            return "Failed to encode data"
        case .decodingFailed:
            return "Failed to decode data"
        case .branchNotFound:
            return "Branch not found"
        }
    }
}
