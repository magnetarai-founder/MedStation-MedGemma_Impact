//
//  SessionBranch.swift
//  MagnetarStudio
//
//  Session branching for topic-based context isolation.
//  Addresses Gap 3: Allows conversations to branch when topics shift.
//

import Foundation

// MARK: - Session Branch

/// A branch of a conversation for topic isolation
struct SessionBranch: Codable, Identifiable, Sendable {
    let id: UUID
    let parentSessionId: UUID
    var branchName: String
    var branchTopic: String
    let createdAt: Date
    var updatedAt: Date

    /// Snapshot of context at branch point
    var contextSnapshot: ContextSnapshot

    /// Message IDs in this branch (after branch point)
    var messageIds: [UUID]

    /// Whether this branch is currently active
    var isActive: Bool

    /// Whether this branch has been merged back
    var isMerged: Bool

    /// If merged, the message ID where it was merged
    var mergedAtMessageId: UUID?

    init(
        id: UUID = UUID(),
        parentSessionId: UUID,
        branchName: String,
        branchTopic: String,
        contextSnapshot: ContextSnapshot,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        messageIds: [UUID] = [],
        isActive: Bool = true,
        isMerged: Bool = false,
        mergedAtMessageId: UUID? = nil
    ) {
        self.id = id
        self.parentSessionId = parentSessionId
        self.branchName = branchName
        self.branchTopic = branchTopic
        self.contextSnapshot = contextSnapshot
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.messageIds = messageIds
        self.isActive = isActive
        self.isMerged = isMerged
        self.mergedAtMessageId = mergedAtMessageId
    }

    /// Message count in this branch
    var messageCount: Int {
        return messageIds.count
    }
}

// MARK: - Context Snapshot

/// Snapshot of context at a point in time (for branch creation)
struct ContextSnapshot: Codable, Sendable {
    let snapshotAt: Date
    let messageCount: Int
    let lastMessageId: UUID?

    /// Compressed summary of context at this point
    let summary: String

    /// Key entities known at this point
    let knownEntities: [String]

    /// Active themes at this point
    let activeThemeIds: [UUID]

    /// Files referenced up to this point
    let referencedFileIds: [UUID]

    init(
        snapshotAt: Date = Date(),
        messageCount: Int = 0,
        lastMessageId: UUID? = nil,
        summary: String = "",
        knownEntities: [String] = [],
        activeThemeIds: [UUID] = [],
        referencedFileIds: [UUID] = []
    ) {
        self.snapshotAt = snapshotAt
        self.messageCount = messageCount
        self.lastMessageId = lastMessageId
        self.summary = summary
        self.knownEntities = knownEntities
        self.activeThemeIds = activeThemeIds
        self.referencedFileIds = referencedFileIds
    }
}

// MARK: - Topic Shift Result

/// Result of topic shift detection
enum TopicShiftResult {
    /// No significant topic shift detected
    case noShift

    /// Minor shift - related topic
    case minorShift(confidence: Float, newTopic: String)

    /// Major shift - completely different topic
    case majorShift(confidence: Float, newTopic: String, suggestedBranchName: String)

    var isSignificant: Bool {
        switch self {
        case .noShift, .minorShift:
            return false
        case .majorShift:
            return true
        }
    }

    var confidence: Float {
        switch self {
        case .noShift:
            return 0.0
        case .minorShift(let conf, _):
            return conf
        case .majorShift(let conf, _, _):
            return conf
        }
    }
}

// MARK: - Branch Suggestion

/// Suggestion for creating a branch
struct BranchSuggestion: Identifiable {
    let id = UUID()
    let reason: String
    let suggestedName: String
    let suggestedTopic: String
    let confidence: Float
    let detectedAt: Date

    init(
        reason: String,
        suggestedName: String,
        suggestedTopic: String,
        confidence: Float,
        detectedAt: Date = Date()
    ) {
        self.reason = reason
        self.suggestedName = suggestedName
        self.suggestedTopic = suggestedTopic
        self.confidence = confidence
        self.detectedAt = detectedAt
    }
}

// MARK: - Branch Action

/// User action on a branch suggestion
enum BranchAction {
    case createBranch(name: String, topic: String)
    case continueCurrent
    case dismiss
}

// MARK: - Branch State

/// State of branches for a session
struct BranchState: Codable, Sendable {
    let sessionId: UUID
    var branches: [SessionBranch]
    var activeBranchId: UUID?
    var lastBranchSuggestionAt: Date?

    init(
        sessionId: UUID,
        branches: [SessionBranch] = [],
        activeBranchId: UUID? = nil,
        lastBranchSuggestionAt: Date? = nil
    ) {
        self.sessionId = sessionId
        self.branches = branches
        self.activeBranchId = activeBranchId
        self.lastBranchSuggestionAt = lastBranchSuggestionAt
    }

    /// Get the active branch (or nil if on main)
    var activeBranch: SessionBranch? {
        guard let activeId = activeBranchId else { return nil }
        return branches.first { $0.id == activeId }
    }

    /// Check if on main branch
    var isOnMainBranch: Bool {
        return activeBranchId == nil
    }

    /// Get all non-merged branches
    var openBranches: [SessionBranch] {
        return branches.filter { !$0.isMerged }
    }
}
