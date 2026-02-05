//
//  ReferenceIndex.swift
//  MagnetarStudio
//
//  REF token system for on-demand context expansion.
//  Enables [REF:topic_abc123] markers that expand when needed.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ReferenceIndex")

// MARK: - Reference Index

/// Manages REF tokens for on-demand context expansion
@MainActor
final class ReferenceIndex {

    // MARK: - Properties

    /// Current index mapping REF IDs to pointers
    private var index: [String: ReferencePointer] = [:]

    /// Conversation ID this index belongs to
    private let conversationId: UUID

    /// Storage service for persistence
    private let storageService: ConversationStorageService

    // MARK: - Configuration

    /// Maximum number of REF tokens to keep
    private let maxRefs = 1000

    // MARK: - Initialization

    init(conversationId: UUID, storageService: ConversationStorageService? = nil) {
        self.conversationId = conversationId
        self.storageService = storageService ?? .shared

        // Load existing index
        self.index = self.storageService.loadReferenceIndex(conversationId)
        logger.debug("[ReferenceIndex] Loaded \(self.index.count) refs for conversation \(conversationId)")
    }

    // MARK: - Index Operations

    /// Add a reference to the index
    func addReference(
        refId: String,
        type: ReferencePointer.ReferenceType,
        targetId: UUID,
        preview: String
    ) {
        let pointer = ReferencePointer(type: type, targetId: targetId, preview: preview)
        index[refId] = pointer

        // Prune if too large
        if index.count > maxRefs {
            pruneOldestRefs()
        }

        // Persist
        save()
        logger.debug("[ReferenceIndex] Added ref: \(refId)")
    }

    /// Add a reference from a theme
    func addReference(for theme: ConversationTheme) {
        let refId = generateRefId(for: theme)
        let preview = String(theme.content.prefix(100))
        addReference(refId: refId, type: .theme, targetId: theme.id, preview: preview)
    }

    /// Add a reference from a semantic node
    func addReference(for node: SemanticNode) {
        let preview = String(node.content.prefix(100))
        addReference(refId: node.refToken, type: .semanticNode, targetId: node.id, preview: preview)
    }

    /// Add a reference for a file
    func addReference(for file: FileReference) {
        let refId = "[REF:file_\(String(file.id.uuidString.prefix(8)))]"
        let preview = "File: \(file.filename)"
        addReference(refId: refId, type: .file, targetId: file.id, preview: preview)
    }

    /// Get a reference pointer
    func getPointer(for refId: String) -> ReferencePointer? {
        return index[refId]
    }

    /// Check if a REF ID exists
    func hasReference(_ refId: String) -> Bool {
        return index[refId] != nil
    }

    /// Get all REF IDs
    var allRefIds: [String] {
        return Array(index.keys)
    }

    /// Get count of references
    var count: Int {
        return index.count
    }

    // MARK: - REF Token Detection

    /// Find all REF tokens in a text
    func findRefTokens(in text: String) -> [String] {
        let pattern = "\\[REF:[\\w_]+\\]"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            logger.warning("[ReferenceIndex] Failed to compile regex for REF token detection")
            return []
        }

        let range = NSRange(text.startIndex..., in: text)
        let matches = regex.matches(in: text, options: [], range: range)

        return matches.compactMap { match -> String? in
            guard let swiftRange = Range(match.range, in: text) else { return nil }
            return String(text[swiftRange])
        }
    }

    /// Find matching REF tokens based on query entities
    func findMatchingRefs(for query: String, limit: Int = 5) -> [String] {
        let queryWords = Set(query.lowercased().components(separatedBy: .whitespacesAndNewlines))

        // Score each ref by preview word overlap
        var scores: [(String, Int)] = []

        for (refId, pointer) in index {
            let previewWords = Set(pointer.preview.lowercased().components(separatedBy: .whitespacesAndNewlines))
            let overlap = queryWords.intersection(previewWords).count
            if overlap > 0 {
                scores.append((refId, overlap))
            }
        }

        return scores
            .sorted { $0.1 > $1.1 }
            .prefix(limit)
            .map { $0.0 }
    }

    // MARK: - Expansion

    /// Expand a single REF token to its content
    func expandReference(_ refId: String) async -> String? {
        guard let pointer = index[refId] else {
            logger.warning("[ReferenceIndex] Unknown ref: \(refId)")
            return nil
        }

        switch pointer.type {
        case .theme:
            let themes = storageService.loadThemes(conversationId)
            return themes.first { $0.id == pointer.targetId }?.content

        case .semanticNode:
            // Would load from semantic node store
            return pointer.preview // Fallback to preview

        case .message:
            // Would load from message store
            return pointer.preview

        case .file:
            return storageService.loadFileContent(pointer.targetId, conversationId: conversationId)

        case .workflow:
            return "Workflow: \(pointer.preview)"

        case .kanbanTask:
            return "Task: \(pointer.preview)"
        }
    }

    /// Expand all REF tokens in a text
    func expandAllReferences(in text: String) async -> String {
        var result = text
        let refs = findRefTokens(in: text)

        for ref in refs {
            if let expanded = await expandReference(ref) {
                result = result.replacingOccurrences(of: ref, with: expanded)
            }
        }

        return result
    }

    /// Expand only the most relevant REF tokens (to stay within token budget)
    func expandRelevantReferences(
        in text: String,
        query: String,
        maxExpansions: Int = 3
    ) async -> String {
        var result = text
        let refs = findRefTokens(in: text)
        let matchingRefs = findMatchingRefs(for: query, limit: maxExpansions)

        // Only expand refs that match the query
        let refsToExpand = refs.filter { matchingRefs.contains($0) }

        for ref in refsToExpand.prefix(maxExpansions) {
            if let expanded = await expandReference(ref) {
                result = result.replacingOccurrences(of: ref, with: expanded)
            }
        }

        return result
    }

    // MARK: - Helpers

    /// Generate REF ID for a theme
    private func generateRefId(for theme: ConversationTheme) -> String {
        let shortId = String(theme.id.uuidString.prefix(8))
        let safeTopic = theme.topic
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .filter { $0.isLetter || $0.isNumber || $0 == "_" }
            .prefix(20)
        return "[REF:\(safeTopic)_\(shortId)]"
    }

    /// Prune oldest references to stay under limit
    private func pruneOldestRefs() {
        // Sort by creation date and remove oldest
        let sorted = index.sorted { $0.value.createdAt < $1.value.createdAt }
        let toRemove = sorted.prefix(index.count - maxRefs + 100) // Remove 100 extra for buffer

        for (key, _) in toRemove {
            index.removeValue(forKey: key)
        }

        logger.info("[ReferenceIndex] Pruned \(toRemove.count) old refs")
    }

    /// Save index to storage
    private func save() {
        do {
            try storageService.saveReferenceIndex(index, conversationId: conversationId)
        } catch {
            logger.error("[ReferenceIndex] Failed to save: \(error)")
        }
    }

    /// Reload index from storage
    func reload() {
        index = storageService.loadReferenceIndex(conversationId)
    }
}
