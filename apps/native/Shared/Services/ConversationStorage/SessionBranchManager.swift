//
//  SessionBranchManager.swift
//  MagnetarStudio
//
//  Manages session branching for topic-based context isolation.
//  Addresses Gap 3: Session branching with topic shift detection.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "SessionBranchManager")

// MARK: - Session Branch Manager

@MainActor
final class SessionBranchManager {

    // MARK: - Dependencies

    private let storageService: ConversationStorageService
    private let embedder: HashEmbedder
    private let themeExtractor: ThemeExtractor

    // MARK: - Configuration

    /// Minimum similarity for "same topic"
    let sameTopicThreshold: Float = 0.7

    /// Maximum similarity for "major shift"
    let majorShiftThreshold: Float = 0.3

    /// Minimum messages before suggesting a branch
    let minMessagesForBranch = 5

    /// Cooldown between branch suggestions (seconds)
    let branchSuggestionCooldown: TimeInterval = 300  // 5 minutes

    // MARK: - State

    private var branchStates: [UUID: BranchState] = [:]

    // MARK: - Singleton

    static let shared = SessionBranchManager()

    // MARK: - Initialization

    init(
        storageService: ConversationStorageService? = nil,
        embedder: HashEmbedder? = nil,
        themeExtractor: ThemeExtractor? = nil
    ) {
        self.storageService = storageService ?? .shared
        self.embedder = embedder ?? .shared
        self.themeExtractor = themeExtractor ?? .shared
    }

    // MARK: - Topic Shift Detection

    /// Detect if there's a significant topic shift
    func detectTopicShift(
        currentMessages: [ChatMessage],
        newMessage: ChatMessage
    ) -> TopicShiftResult {
        guard currentMessages.count >= minMessagesForBranch else {
            return .noShift
        }

        // Get recent context (last 10 messages)
        let recentMessages = currentMessages.suffix(10)
        let recentContent = recentMessages.map { $0.content }.joined(separator: " ")

        // Embed recent context and new message
        let recentEmbedding = embedder.embed(recentContent)
        let newEmbedding = embedder.embed(newMessage.content)

        // Calculate similarity
        let similarity = HashEmbedder.cosineSimilarity(recentEmbedding, newEmbedding)

        // Determine shift type
        if similarity >= sameTopicThreshold {
            return .noShift
        } else if similarity >= majorShiftThreshold {
            let topic = extractTopicFromMessage(newMessage)
            return .minorShift(confidence: 1.0 - similarity, newTopic: topic)
        } else {
            let topic = extractTopicFromMessage(newMessage)
            let branchName = generateBranchName(from: topic)
            return .majorShift(
                confidence: 1.0 - similarity,
                newTopic: topic,
                suggestedBranchName: branchName
            )
        }
    }

    /// Suggest a branch based on topic shift
    func suggestBranch(
        for shift: TopicShiftResult,
        sessionId: UUID
    ) -> BranchSuggestion? {
        // Check cooldown
        if let state = branchStates[sessionId],
           let lastSuggestion = state.lastBranchSuggestionAt,
           Date().timeIntervalSince(lastSuggestion) < branchSuggestionCooldown {
            return nil
        }

        switch shift {
        case .noShift, .minorShift:
            return nil

        case .majorShift(let confidence, let newTopic, let suggestedName):
            // Update last suggestion time
            if branchStates[sessionId] == nil {
                branchStates[sessionId] = BranchState(sessionId: sessionId)
            }
            branchStates[sessionId]?.lastBranchSuggestionAt = Date()

            return BranchSuggestion(
                reason: "Detected significant topic change",
                suggestedName: suggestedName,
                suggestedTopic: newTopic,
                confidence: confidence
            )
        }
    }

    // MARK: - Branch Operations

    /// Create a new branch from the current session state
    func createBranch(
        from sessionId: UUID,
        name: String,
        topic: String,
        currentMessages: [ChatMessage]
    ) async -> SessionBranch {
        // Create context snapshot
        let snapshot = createSnapshot(from: currentMessages, sessionId: sessionId)

        // Create branch
        let branch = SessionBranch(
            parentSessionId: sessionId,
            branchName: name,
            branchTopic: topic,
            contextSnapshot: snapshot
        )

        // Update state
        if branchStates[sessionId] == nil {
            branchStates[sessionId] = BranchState(sessionId: sessionId)
        }
        branchStates[sessionId]?.branches.append(branch)
        branchStates[sessionId]?.activeBranchId = branch.id

        // Persist
        saveBranchState(sessionId)

        logger.info("[SessionBranch] Created branch '\(name)' for session \(sessionId)")
        return branch
    }

    /// Switch to a different branch
    func switchToBranch(_ branchId: UUID?, sessionId: UUID) {
        branchStates[sessionId]?.activeBranchId = branchId
        saveBranchState(sessionId)

        if let branchId = branchId {
            logger.info("[SessionBranch] Switched to branch \(branchId)")
        } else {
            logger.info("[SessionBranch] Switched to main branch")
        }
    }

    /// Merge a branch back into the main session
    func mergeBranch(
        _ branchId: UUID,
        into sessionId: UUID,
        atMessageId: UUID
    ) {
        guard let index = branchStates[sessionId]?.branches.firstIndex(where: { $0.id == branchId }) else {
            logger.warning("[SessionBranch] Branch not found for merge: \(branchId)")
            return
        }

        branchStates[sessionId]?.branches[index].isMerged = true
        branchStates[sessionId]?.branches[index].mergedAtMessageId = atMessageId
        branchStates[sessionId]?.branches[index].isActive = false

        // If we're on the merged branch, switch to main
        if branchStates[sessionId]?.activeBranchId == branchId {
            branchStates[sessionId]?.activeBranchId = nil
        }

        saveBranchState(sessionId)
        logger.info("[SessionBranch] Merged branch \(branchId) into session \(sessionId)")
    }

    /// Delete a branch (only if not merged)
    func deleteBranch(_ branchId: UUID, sessionId: UUID) {
        guard let state = branchStates[sessionId],
              let branch = state.branches.first(where: { $0.id == branchId }),
              !branch.isMerged else {
            logger.warning("[SessionBranch] Cannot delete merged or non-existent branch")
            return
        }

        branchStates[sessionId]?.branches.removeAll { $0.id == branchId }

        if branchStates[sessionId]?.activeBranchId == branchId {
            branchStates[sessionId]?.activeBranchId = nil
        }

        saveBranchState(sessionId)
        logger.info("[SessionBranch] Deleted branch \(branchId)")
    }

    /// Get all branches for a session
    func branches(for sessionId: UUID) -> [SessionBranch] {
        return branchStates[sessionId]?.branches ?? []
    }

    /// Get current branch state for a session
    func getBranchState(_ sessionId: UUID) -> BranchState? {
        return branchStates[sessionId]
    }

    /// Add a message to the active branch
    func addMessageToBranch(_ messageId: UUID, sessionId: UUID) {
        guard let activeBranchId = branchStates[sessionId]?.activeBranchId,
              let index = branchStates[sessionId]?.branches.firstIndex(where: { $0.id == activeBranchId }) else {
            return
        }

        branchStates[sessionId]?.branches[index].messageIds.append(messageId)
        branchStates[sessionId]?.branches[index].updatedAt = Date()
        saveBranchState(sessionId)
    }

    // MARK: - Helpers

    /// Extract topic from a message
    private func extractTopicFromMessage(_ message: ChatMessage) -> String {
        let words = message.content.components(separatedBy: .whitespacesAndNewlines)
        return words.prefix(5).joined(separator: " ")
    }

    /// Generate a branch name from a topic
    private func generateBranchName(from topic: String) -> String {
        let words = topic.components(separatedBy: .whitespacesAndNewlines)
        let name = words.prefix(3).joined(separator: "-").lowercased()
        return name.isEmpty ? "branch-\(Date().timeIntervalSince1970.truncatingRemainder(dividingBy: 10000))" : name
    }

    /// Create a context snapshot from current messages
    private func createSnapshot(from messages: [ChatMessage], sessionId: UUID) -> ContextSnapshot {
        // Get known entities from themes
        let themes = storageService.loadThemes(sessionId)
        let entities = themes.flatMap { $0.entities }

        // Get referenced files
        let files = storageService.loadFileReferences(sessionId)
        let fileIds = files.map { $0.id }

        // Create summary
        let recentContent = messages.suffix(5).map { $0.content }.joined(separator: " ")
        let summary = String(recentContent.prefix(200))

        return ContextSnapshot(
            messageCount: messages.count,
            lastMessageId: messages.last?.id,
            summary: summary,
            knownEntities: Array(Set(entities)),
            activeThemeIds: themes.map { $0.id },
            referencedFileIds: fileIds
        )
    }

    /// Save branch state to storage
    private func saveBranchState(_ sessionId: UUID) {
        // Would persist to ConversationStorageService
        // For now, kept in memory
    }

    /// Load branch state from storage
    func loadBranchState(_ sessionId: UUID) {
        // Would load from ConversationStorageService
        if branchStates[sessionId] == nil {
            branchStates[sessionId] = BranchState(sessionId: sessionId)
        }
    }
}
