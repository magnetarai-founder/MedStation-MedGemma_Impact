//
//  SessionGraphBuilder.swift
//  MagnetarStudio
//
//  Full entity relationship graph for conversation context.
//  Addresses Gap 1: Entity relationships, not just extractions.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "SessionGraph")

// MARK: - Session Graph

/// Graph of entity relationships within a conversation
struct SessionGraph: Codable {
    var nodes: [EntityNode]
    var edges: [EntityRelationship]
    var createdAt: Date
    var updatedAt: Date

    init(
        nodes: [EntityNode] = [],
        edges: [EntityRelationship] = [],
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.nodes = nodes
        self.edges = edges
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    // MARK: - Query Methods

    /// Find entities related to a given entity
    func relatedEntities(to entityId: UUID, limit: Int = 10) -> [EntityNode] {
        // Find edges connected to this entity
        let connectedEdges = edges.filter { $0.sourceId == entityId || $0.targetId == entityId }

        // Get connected entity IDs
        let relatedIds = Set(connectedEdges.flatMap { edge -> [UUID] in
            if edge.sourceId == entityId {
                return [edge.targetId]
            } else {
                return [edge.sourceId]
            }
        })

        // Return matching nodes sorted by mention count
        return nodes
            .filter { relatedIds.contains($0.id) }
            .sorted { $0.mentionCount > $1.mentionCount }
            .prefix(limit)
            .map { $0 }
    }

    /// Find path between two entities
    func pathBetween(source: UUID, target: UUID) -> [EntityRelationship]? {
        // Simple BFS for path finding
        var visited = Set<UUID>()
        var queue: [(UUID, [EntityRelationship])] = [(source, [])]

        while !queue.isEmpty {
            let (current, path) = queue.removeFirst()

            if current == target {
                return path
            }

            if visited.contains(current) { continue }
            visited.insert(current)

            // Find edges from current node
            let outgoingEdges = edges.filter { $0.sourceId == current || $0.targetId == current }

            for edge in outgoingEdges {
                let nextId = edge.sourceId == current ? edge.targetId : edge.sourceId
                if !visited.contains(nextId) {
                    queue.append((nextId, path + [edge]))
                }
            }
        }

        return nil // No path found
    }

    /// Get strongest relationships in the graph
    func strongestRelationships(limit: Int = 10) -> [EntityRelationship] {
        return edges
            .sorted { $0.strength > $1.strength }
            .prefix(limit)
            .map { $0 }
    }

    /// Find entity by name (case-insensitive)
    func findEntity(named name: String) -> EntityNode? {
        return nodes.first { $0.name.lowercased() == name.lowercased() }
    }

    /// Get all entities of a specific type
    func entities(ofType type: EntityType) -> [EntityNode] {
        return nodes.filter { $0.type == type }
    }
}

// MARK: - Entity Node

/// A node in the session graph representing an entity
struct EntityNode: Codable, Identifiable {
    let id: UUID
    let name: String
    let type: EntityType
    var firstMentioned: Date
    var lastMentioned: Date
    var mentionCount: Int
    var embedding: [Float]?
    var metadata: [String: String]?

    init(
        id: UUID = UUID(),
        name: String,
        type: EntityType,
        firstMentioned: Date = Date(),
        lastMentioned: Date = Date(),
        mentionCount: Int = 1,
        embedding: [Float]? = nil,
        metadata: [String: String]? = nil
    ) {
        self.id = id
        self.name = name
        self.type = type
        self.firstMentioned = firstMentioned
        self.lastMentioned = lastMentioned
        self.mentionCount = mentionCount
        self.embedding = embedding
        self.metadata = metadata
    }

    /// Update mention tracking
    mutating func recordMention() {
        mentionCount += 1
        lastMentioned = Date()
    }
}

// MARK: - Entity Type

/// Types of entities that can be tracked
enum EntityType: String, Codable, CaseIterable {
    case person
    case organization
    case place
    case concept
    case file
    case task
    case workflow
    case codeFile
    case function
    case variable
    case project
    case date
    case amount
    case unknown

    var icon: String {
        switch self {
        case .person: return "person.fill"
        case .organization: return "building.2.fill"
        case .place: return "mappin.circle.fill"
        case .concept: return "lightbulb.fill"
        case .file: return "doc.fill"
        case .task: return "checklist"
        case .workflow: return "arrow.triangle.branch"
        case .codeFile: return "doc.text.fill"
        case .function: return "function"
        case .variable: return "x.squareroot"
        case .project: return "folder.fill"
        case .date: return "calendar"
        case .amount: return "dollarsign.circle"
        case .unknown: return "questionmark.circle"
        }
    }
}

// MARK: - Entity Relationship

/// A relationship between two entities
struct EntityRelationship: Codable, Identifiable {
    let id: UUID
    let sourceId: UUID
    let targetId: UUID
    let relationshipType: RelationshipType
    var strength: Float
    var context: String?
    var firstOccurrence: Date
    var lastOccurrence: Date
    var occurrenceCount: Int

    init(
        id: UUID = UUID(),
        sourceId: UUID,
        targetId: UUID,
        relationshipType: RelationshipType,
        strength: Float = 1.0,
        context: String? = nil,
        firstOccurrence: Date = Date(),
        lastOccurrence: Date = Date(),
        occurrenceCount: Int = 1
    ) {
        self.id = id
        self.sourceId = sourceId
        self.targetId = targetId
        self.relationshipType = relationshipType
        self.strength = strength
        self.context = context
        self.firstOccurrence = firstOccurrence
        self.lastOccurrence = lastOccurrence
        self.occurrenceCount = occurrenceCount
    }

    /// Record another occurrence of this relationship
    mutating func recordOccurrence(context: String? = nil) {
        occurrenceCount += 1
        lastOccurrence = Date()
        strength = min(1.0, strength + 0.1)  // Increase strength with repetition
        if let newContext = context {
            self.context = newContext
        }
    }
}

// MARK: - Relationship Type

/// Types of relationships between entities
enum RelationshipType: String, Codable, CaseIterable {
    case mentionedWith = "mentioned_with"
    case causedBy = "caused_by"
    case dependsOn = "depends_on"
    case createdBy = "created_by"
    case assignedTo = "assigned_to"
    case partOf = "part_of"
    case references = "references"
    case relatedTo = "related_to"
    case blocks = "blocks"
    case implements = "implements"
    case calls = "calls"
    case contains = "contains"

    var description: String {
        switch self {
        case .mentionedWith: return "mentioned with"
        case .causedBy: return "caused by"
        case .dependsOn: return "depends on"
        case .createdBy: return "created by"
        case .assignedTo: return "assigned to"
        case .partOf: return "part of"
        case .references: return "references"
        case .relatedTo: return "related to"
        case .blocks: return "blocks"
        case .implements: return "implements"
        case .calls: return "calls"
        case .contains: return "contains"
        }
    }
}

// MARK: - Session Graph Builder

/// Builds and updates the session graph from conversation messages
@MainActor
final class SessionGraphBuilder {

    // MARK: - Dependencies

    private var graph: SessionGraph
    private var entityNameToId: [String: UUID] = [:]

    // MARK: - Configuration

    /// Minimum co-occurrence count to create a relationship
    let minCoOccurrences = 2

    /// Relationship strength decay per day
    let strengthDecayRate: Float = 0.05

    // MARK: - Singleton

    static let shared = SessionGraphBuilder()

    // MARK: - Initialization

    init(graph: SessionGraph? = nil) {
        self.graph = graph ?? SessionGraph()

        // Build name-to-id index
        for node in self.graph.nodes {
            entityNameToId[node.name.lowercased()] = node.id
        }
    }

    // MARK: - Graph Access

    /// Get current graph
    func getGraph() -> SessionGraph {
        return graph
    }

    /// Set/replace the graph
    func setGraph(_ newGraph: SessionGraph) {
        self.graph = newGraph
        entityNameToId.removeAll()
        for node in graph.nodes {
            entityNameToId[node.name.lowercased()] = node.id
        }
    }

    // MARK: - Entity Management

    /// Add or update an entity in the graph
    @discardableResult
    func addEntity(name: String, type: EntityType, embedding: [Float]? = nil) -> EntityNode {
        let normalizedName = name.lowercased()

        if let existingId = entityNameToId[normalizedName],
           let index = graph.nodes.firstIndex(where: { $0.id == existingId }) {
            // Update existing entity
            graph.nodes[index].recordMention()
            if let embedding = embedding {
                graph.nodes[index].embedding = embedding
            }
            graph.updatedAt = Date()
            return graph.nodes[index]
        } else {
            // Create new entity
            let node = EntityNode(
                name: name,
                type: type,
                embedding: embedding
            )
            graph.nodes.append(node)
            entityNameToId[normalizedName] = node.id
            graph.updatedAt = Date()
            logger.debug("[SessionGraph] Added entity: \(name) (\(type.rawValue))")
            return node
        }
    }

    /// Add or strengthen a relationship between entities
    @discardableResult
    func addRelationship(
        from sourceName: String,
        to targetName: String,
        type: RelationshipType,
        context: String? = nil
    ) -> EntityRelationship? {
        guard let sourceId = entityNameToId[sourceName.lowercased()],
              let targetId = entityNameToId[targetName.lowercased()] else {
            logger.warning("[SessionGraph] Cannot create relationship: entity not found")
            return nil
        }

        // Check if relationship exists
        if let index = graph.edges.firstIndex(where: {
            ($0.sourceId == sourceId && $0.targetId == targetId) ||
            ($0.sourceId == targetId && $0.targetId == sourceId)
        }) {
            // Strengthen existing relationship
            graph.edges[index].recordOccurrence(context: context)
            graph.updatedAt = Date()
            return graph.edges[index]
        } else {
            // Create new relationship
            let edge = EntityRelationship(
                sourceId: sourceId,
                targetId: targetId,
                relationshipType: type,
                context: context
            )
            graph.edges.append(edge)
            graph.updatedAt = Date()
            logger.debug("[SessionGraph] Added relationship: \(sourceName) -> \(targetName)")
            return edge
        }
    }

    /// Extract entities from text (simple heuristic)
    func extractEntities(from text: String) -> [(name: String, type: EntityType)] {
        var entities: [(String, EntityType)] = []

        // Simple heuristics for entity extraction
        let words = text.components(separatedBy: .whitespacesAndNewlines)
        var wordCounts: [String: Int] = [:]

        for word in words {
            let cleaned = word.trimmingCharacters(in: .punctuationCharacters)
            guard cleaned.count > 2 else { continue }
            wordCounts[cleaned, default: 0] += 1
        }

        // Capitalized words that appear multiple times (likely proper nouns)
        for (word, count) in wordCounts where count >= 2 {
            if let first = word.first, first.isUppercase {
                let type = inferEntityType(word)
                entities.append((word, type))
            }
        }

        // Look for file paths
        let filePattern = try? NSRegularExpression(pattern: "[\\w/]+\\.[a-zA-Z]{2,4}", options: [])
        let range = NSRange(text.startIndex..., in: text)
        if let matches = filePattern?.matches(in: text, options: [], range: range) {
            for match in matches {
                if let swiftRange = Range(match.range, in: text) {
                    let path = String(text[swiftRange])
                    entities.append((path, .file))
                }
            }
        }

        return entities
    }

    /// Infer entity type from name
    private func inferEntityType(_ name: String) -> EntityType {
        let lowered = name.lowercased()

        // Check for code-related
        if lowered.hasSuffix(".swift") || lowered.hasSuffix(".py") ||
           lowered.hasSuffix(".ts") || lowered.hasSuffix(".js") {
            return .codeFile
        }

        // Check for function patterns
        if lowered.contains("()") || lowered.hasPrefix("func") ||
           lowered.hasPrefix("def ") || lowered.contains("function") {
            return .function
        }

        // Check for date patterns
        if lowered.contains("january") || lowered.contains("february") ||
           lowered.contains("q1") || lowered.contains("q2") ||
           lowered.contains("q3") || lowered.contains("q4") {
            return .date
        }

        // Check for monetary
        if lowered.hasPrefix("$") || lowered.hasSuffix("k") ||
           lowered.hasSuffix("m") || lowered.hasSuffix("b") {
            return .amount
        }

        return .concept
    }

    /// Process a message and update the graph
    func processMessage(_ content: String) {
        let entities = extractEntities(from: content)

        // Add all entities
        for (name, type) in entities {
            addEntity(name: name, type: type)
        }

        // Create co-occurrence relationships
        for i in 0..<entities.count {
            for j in (i+1)..<entities.count {
                addRelationship(
                    from: entities[i].name,
                    to: entities[j].name,
                    type: .mentionedWith
                )
            }
        }
    }

    /// Apply decay to relationship strengths (call periodically)
    func applyDecay() {
        let now = Date()
        for i in 0..<graph.edges.count {
            let daysSinceUpdate = now.timeIntervalSince(graph.edges[i].lastOccurrence) / 86400
            let decay = Float(daysSinceUpdate) * strengthDecayRate
            graph.edges[i].strength = max(0.1, graph.edges[i].strength - decay)
        }
        graph.updatedAt = now
    }
}
