//
//  DetachedWorkspaceInfo.swift
//  MagnetarStudio
//
//  Data models for pop-out workspace windows.
//  Must be Hashable for WindowGroup(for:) binding.
//

import Foundation

/// Info for popping out a document editor to its own window
struct DetachedDocEditInfo: Identifiable, Hashable, Codable {
    let id: UUID
    var title: String
    var storagePath: String  // Relative path in workspace/docs/

    init(id: UUID = UUID(), title: String = "Document", storagePath: String = "") {
        self.id = id
        self.title = title
        self.storagePath = storagePath
    }
}

/// Info for popping out a spreadsheet to its own window
struct DetachedSheetInfo: Identifiable, Hashable, Codable {
    let id: UUID
    var title: String
    var storagePath: String  // Relative path in workspace/sheets/

    init(id: UUID = UUID(), title: String = "Spreadsheet", storagePath: String = "") {
        self.id = id
        self.title = title
        self.storagePath = storagePath
    }
}

/// Info for popping out a PDF viewer to its own window
struct DetachedPDFViewInfo: Identifiable, Hashable, Codable {
    let id: UUID
    var title: String
    var fileURL: URL

    init(id: UUID = UUID(), title: String = "PDF", fileURL: URL) {
        self.id = id
        self.title = title
        self.fileURL = fileURL
    }
}
