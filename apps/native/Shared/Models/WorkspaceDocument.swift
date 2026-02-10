//
//  WorkspaceDocument.swift
//  MedStation
//
//  Document model for the Docs panel — Notion + Word hybrid.
//

import Foundation

struct WorkspaceDocument: Identifiable, Codable, Equatable, Hashable, Sendable {
    let id: UUID
    var title: String
    var content: String
    var createdAt: Date
    var updatedAt: Date
    var tags: [String]
    var isStarred: Bool

    var wordCount: Int {
        content.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count
    }

    init(
        id: UUID = UUID(),
        title: String = "Untitled Document",
        content: String = "",
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        tags: [String] = [],
        isStarred: Bool = false
    ) {
        self.id = id
        self.title = title
        self.content = content
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.tags = tags
        self.isStarred = isStarred
    }

    mutating func updateContent(_ newContent: String) {
        content = newContent
        updatedAt = Date()
    }
}
