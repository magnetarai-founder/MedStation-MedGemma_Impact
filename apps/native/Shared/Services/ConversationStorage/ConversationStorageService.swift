//
//  ConversationStorageService.swift
//  MagnetarStudio
//
//  Hierarchical conversation storage inspired by Claude Code's .claude/ folder.
//  Manages persistent storage of conversations, themes, and file references.
//
//  Directory Structure:
//  .magnetar_studio/
//  ├── conversations/
//  │   └── conv_[uuid]/
//  │       ├── metadata.json
//  │       ├── hierarchy/
//  │       │   ├── themes/
//  │       │   ├── semantic_nodes/
//  │       │   ├── session_graph.json
//  │       │   └── compressed_context.json
//  │       ├── files/
//  │       └── reference_index.json
//  ├── user_model/
//  └── global_files/
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ConversationStorage")

// MARK: - Conversation Storage Service

@MainActor
final class ConversationStorageService {

    // MARK: - Properties

    private let fileManager = FileManager.default
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    /// Root directory for all storage
    private let rootDirectory: URL

    // MARK: - Singleton

    static let shared = ConversationStorageService()

    // MARK: - Initialization

    init() {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.rootDirectory = documentsPath.appendingPathComponent(".magnetar_studio", isDirectory: true)

        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        setupDirectoryStructure()
        logger.info("[ConversationStorage] Initialized at \(self.rootDirectory.path)")
    }

    // MARK: - Directory Setup

    private func setupDirectoryStructure() {
        let directories = [
            rootDirectory,
            rootDirectory.appendingPathComponent("conversations"),
            rootDirectory.appendingPathComponent("user_model"),
            rootDirectory.appendingPathComponent("global_files")
        ]

        for dir in directories {
            try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        }
    }

    private func conversationDirectory(_ id: UUID) -> URL {
        rootDirectory.appendingPathComponent("conversations/conv_\(id.uuidString)")
    }

    private func ensureConversationDirectory(_ id: UUID) {
        let convDir = conversationDirectory(id)
        let subdirs = ["hierarchy/themes", "hierarchy/semantic_nodes", "files", "embeddings"]

        for subdir in subdirs {
            let path = convDir.appendingPathComponent(subdir)
            try? fileManager.createDirectory(at: path, withIntermediateDirectories: true)
        }
    }

    // MARK: - Metadata Operations

    /// Save conversation metadata
    func saveMetadata(_ metadata: ConversationMetadata) throws {
        ensureConversationDirectory(metadata.id)
        let url = conversationDirectory(metadata.id).appendingPathComponent("metadata.json")
        let data = try encoder.encode(metadata)
        try data.write(to: url)
        logger.debug("[ConversationStorage] Saved metadata for \(metadata.id)")
    }

    /// Load conversation metadata
    func loadMetadata(_ id: UUID) -> ConversationMetadata? {
        let url = conversationDirectory(id).appendingPathComponent("metadata.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(ConversationMetadata.self, from: data)
    }

    /// List all conversation IDs
    func listConversations() -> [UUID] {
        let conversationsDir = rootDirectory.appendingPathComponent("conversations")
        guard let contents = try? fileManager.contentsOfDirectory(at: conversationsDir, includingPropertiesForKeys: nil) else {
            return []
        }

        return contents.compactMap { url -> UUID? in
            let name = url.lastPathComponent
            guard name.hasPrefix("conv_") else { return nil }
            let uuidString = String(name.dropFirst(5))
            return UUID(uuidString: uuidString)
        }
    }

    // MARK: - Theme Operations

    /// Save a theme to the conversation hierarchy
    func saveTheme(_ theme: ConversationTheme, conversationId: UUID) throws {
        ensureConversationDirectory(conversationId)
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/themes/theme_\(theme.id.uuidString).json")
        let data = try encoder.encode(theme)
        try data.write(to: url)
    }

    /// Load all themes for a conversation
    func loadThemes(_ conversationId: UUID) -> [ConversationTheme] {
        let themesDir = conversationDirectory(conversationId).appendingPathComponent("hierarchy/themes")
        guard let contents = try? fileManager.contentsOfDirectory(at: themesDir, includingPropertiesForKeys: nil) else {
            return []
        }

        return contents.compactMap { url -> ConversationTheme? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(ConversationTheme.self, from: data)
        }
    }

    /// Delete a theme
    func deleteTheme(_ themeId: UUID, conversationId: UUID) {
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/themes/theme_\(themeId.uuidString).json")
        try? fileManager.removeItem(at: url)
    }

    // MARK: - Semantic Node Operations

    /// Save a semantic node
    func saveSemanticNode(_ node: SemanticNode, conversationId: UUID) throws {
        ensureConversationDirectory(conversationId)
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/semantic_nodes/node_\(node.id.uuidString).json")
        let data = try encoder.encode(node)
        try data.write(to: url)
    }

    /// Load all semantic nodes for a conversation
    func loadSemanticNodes(_ conversationId: UUID) -> [SemanticNode] {
        let nodesDir = conversationDirectory(conversationId).appendingPathComponent("hierarchy/semantic_nodes")
        guard let contents = try? fileManager.contentsOfDirectory(at: nodesDir, includingPropertiesForKeys: nil) else {
            return []
        }

        return contents.compactMap { url -> SemanticNode? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(SemanticNode.self, from: data)
        }
    }

    // MARK: - Session Graph Operations

    /// Save session graph
    func saveSessionGraph(_ graph: SessionGraph, conversationId: UUID) throws {
        ensureConversationDirectory(conversationId)
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/session_graph.json")
        let data = try encoder.encode(graph)
        try data.write(to: url)
    }

    /// Load session graph
    func loadSessionGraph(_ conversationId: UUID) -> SessionGraph? {
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/session_graph.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(SessionGraph.self, from: data)
    }

    // MARK: - Compressed Context

    /// Save compressed context for a conversation
    func saveCompressedContext(_ context: CompressedContext, conversationId: UUID) throws {
        ensureConversationDirectory(conversationId)
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/compressed_context.json")
        let data = try encoder.encode(context)
        try data.write(to: url)
    }

    /// Load compressed context
    func loadCompressedContext(_ conversationId: UUID) -> CompressedContext? {
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("hierarchy/compressed_context.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(CompressedContext.self, from: data)
    }

    // MARK: - Reference Index

    /// Save reference index for quick REF ID lookup
    func saveReferenceIndex(_ index: [String: ReferencePointer], conversationId: UUID) throws {
        let url = conversationDirectory(conversationId).appendingPathComponent("reference_index.json")
        let data = try encoder.encode(index)
        try data.write(to: url)
    }

    /// Load reference index
    func loadReferenceIndex(_ conversationId: UUID) -> [String: ReferencePointer] {
        let url = conversationDirectory(conversationId).appendingPathComponent("reference_index.json")
        guard let data = try? Data(contentsOf: url) else { return [:] }
        return (try? decoder.decode([String: ReferencePointer].self, from: data)) ?? [:]
    }

    /// Expand a REF token to its full content
    func expandReference(_ refId: String, conversationId: UUID) -> String? {
        let index = loadReferenceIndex(conversationId)
        guard let pointer = index[refId] else { return nil }

        switch pointer.type {
        case .theme:
            let themes = loadThemes(conversationId)
            return themes.first { $0.id == pointer.targetId }?.content

        case .semanticNode:
            let nodes = loadSemanticNodes(conversationId)
            return nodes.first { $0.id == pointer.targetId }?.content

        case .message:
            return pointer.preview  // Would need message store integration

        case .file:
            return loadFileContent(pointer.targetId, conversationId: conversationId)

        case .workflow, .kanbanTask:
            return pointer.preview  // Would need respective store integration
        }
    }

    // MARK: - File Operations

    /// Save a file reference
    func saveFileReference(_ file: FileReference, conversationId: UUID) throws {
        ensureConversationDirectory(conversationId)
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("files/\(file.id.uuidString).json")
        let data = try encoder.encode(file)
        try data.write(to: url)
    }

    /// Load all file references for a conversation
    func loadFileReferences(_ conversationId: UUID) -> [FileReference] {
        let filesDir = conversationDirectory(conversationId).appendingPathComponent("files")
        guard let contents = try? fileManager.contentsOfDirectory(at: filesDir, includingPropertiesForKeys: nil) else {
            return []
        }

        return contents.compactMap { url -> FileReference? in
            guard url.pathExtension == "json" else { return nil }
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? decoder.decode(FileReference.self, from: data)
        }
    }

    /// Load file content
    func loadFileContent(_ fileId: UUID, conversationId: UUID) -> String? {
        let url = conversationDirectory(conversationId)
            .appendingPathComponent("files/\(fileId.uuidString).json")
        guard let data = try? Data(contentsOf: url),
              let file = try? decoder.decode(FileReference.self, from: data) else {
            return nil
        }
        return file.processedContent
    }

    // MARK: - Full Hierarchy Operations

    /// Load complete conversation hierarchy
    func loadHierarchy(_ conversationId: UUID) -> ConversationHierarchy? {
        guard let metadata = loadMetadata(conversationId) else { return nil }

        return ConversationHierarchy(
            id: conversationId,
            metadata: metadata,
            themes: loadThemes(conversationId),
            sessionGraph: loadSessionGraph(conversationId),
            compressedContext: loadCompressedContext(conversationId),
            fileReferences: loadFileReferences(conversationId),
            referenceIndex: loadReferenceIndex(conversationId)
        )
    }

    /// Save complete conversation hierarchy
    func saveHierarchy(_ hierarchy: ConversationHierarchy) throws {
        try saveMetadata(hierarchy.metadata)

        for theme in hierarchy.themes {
            try saveTheme(theme, conversationId: hierarchy.id)
        }

        if let graph = hierarchy.sessionGraph {
            try saveSessionGraph(graph, conversationId: hierarchy.id)
        }

        if let compressed = hierarchy.compressedContext {
            try saveCompressedContext(compressed, conversationId: hierarchy.id)
        }

        for file in hierarchy.fileReferences {
            try saveFileReference(file, conversationId: hierarchy.id)
        }

        try saveReferenceIndex(hierarchy.referenceIndex, conversationId: hierarchy.id)
    }

    // MARK: - Token Estimation

    /// Estimate total tokens stored for a conversation
    func estimateTotalStoredTokens(_ conversationId: UUID) -> Int {
        var total = 0

        // Themes
        for theme in loadThemes(conversationId) {
            total += theme.content.count / 4  // Rough estimate
        }

        // Semantic nodes
        for node in loadSemanticNodes(conversationId) {
            total += node.content.count / 4
        }

        // Compressed context
        if let compressed = loadCompressedContext(conversationId) {
            total += compressed.summary.count / 4
        }

        // Files
        for file in loadFileReferences(conversationId) {
            if let content = file.processedContent {
                total += content.count / 4
            }
        }

        return total
    }

    // MARK: - Cleanup

    /// Delete a conversation and all its data
    func deleteConversation(_ id: UUID) {
        let dir = conversationDirectory(id)
        try? fileManager.removeItem(at: dir)
        logger.info("[ConversationStorage] Deleted conversation \(id)")
    }

    /// Get storage size for a conversation
    func getStorageSize(_ id: UUID) -> Int64 {
        let dir = conversationDirectory(id)
        return directorySize(at: dir)
    }

    private func directorySize(at url: URL) -> Int64 {
        guard let enumerator = fileManager.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey]) else {
            return 0
        }

        var total: Int64 = 0
        for case let fileURL as URL in enumerator {
            if let size = try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize {
                total += Int64(size)
            }
        }
        return total
    }

    /// Get total storage used by all conversations
    func getTotalStorageSize() -> Int64 {
        return directorySize(at: rootDirectory)
    }
}
