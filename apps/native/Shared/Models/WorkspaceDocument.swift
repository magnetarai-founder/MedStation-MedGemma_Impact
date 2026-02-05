//
//  WorkspaceDocument.swift
//  MagnetarStudio
//
//  Document model for the Docs panel — Notion + Word hybrid.
//

import Foundation

struct WorkspaceDocument: Identifiable, Codable, Equatable, Hashable {
    let id: UUID
    var title: String
    var content: String
    var createdAt: Date
    var updatedAt: Date
    var wordCount: Int
    var tags: [String]
    var isStarred: Bool

    init(
        id: UUID = UUID(),
        title: String = "Untitled Document",
        content: String = "",
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        wordCount: Int = 0,
        tags: [String] = [],
        isStarred: Bool = false
    ) {
        self.id = id
        self.title = title
        self.content = content
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.wordCount = wordCount
        self.tags = tags
        self.isStarred = isStarred
    }

    mutating func updateContent(_ newContent: String) {
        content = newContent
        updatedAt = Date()
        wordCount = newContent.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count
    }
}
