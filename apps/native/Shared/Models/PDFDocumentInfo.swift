//
//  PDFDocumentInfo.swift
//  MagnetarStudio
//
//  Metadata model for imported PDF documents.
//

import Foundation

struct PDFDocumentInfo: Identifiable, Codable, Equatable, Hashable {
    let id: UUID
    var title: String
    var fileURL: URL
    var pageCount: Int
    var fileSize: Int64
    var importedAt: Date
    var lastOpenedAt: Date
    var isStarred: Bool
    var bookmarks: [PDFBookmark]

    init(
        id: UUID = UUID(),
        title: String = "Untitled PDF",
        fileURL: URL,
        pageCount: Int = 0,
        fileSize: Int64 = 0,
        importedAt: Date = Date(),
        lastOpenedAt: Date = Date(),
        isStarred: Bool = false,
        bookmarks: [PDFBookmark] = []
    ) {
        self.id = id
        self.title = title
        self.fileURL = fileURL
        self.pageCount = pageCount
        self.fileSize = fileSize
        self.importedAt = importedAt
        self.lastOpenedAt = lastOpenedAt
        self.isStarred = isStarred
        self.bookmarks = bookmarks
    }
}

struct PDFBookmark: Identifiable, Codable, Equatable, Hashable {
    let id: UUID
    var pageIndex: Int
    var label: String
    var createdAt: Date

    init(id: UUID = UUID(), pageIndex: Int, label: String = "", createdAt: Date = Date()) {
        self.id = id
        self.pageIndex = pageIndex
        self.label = label
        self.createdAt = createdAt
    }
}
