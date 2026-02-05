//
//  SpreadsheetDocument.swift
//  MagnetarStudio
//
//  Spreadsheet document model with sparse cell storage.
//

import Foundation

// MARK: - Cell Address

struct CellAddress: Hashable, Codable, CustomStringConvertible, Sendable {
    let column: Int  // 0-based (A=0, B=1, ...)
    let row: Int     // 0-based

    var description: String {
        "\(Self.columnLetter(column))\(row + 1)"
    }

    static func columnLetter(_ col: Int) -> String {
        var result = ""
        var c = col
        repeat {
            result = String(UnicodeScalar(65 + c % 26)!) + result
            c = c / 26 - 1
        } while c >= 0
        return result
    }

    static func fromString(_ str: String) -> CellAddress? {
        let upper = str.uppercased()
        var colPart = ""
        var rowPart = ""

        for char in upper {
            if char.isLetter { colPart.append(char) }
            else if char.isNumber { rowPart.append(char) }
        }

        guard !colPart.isEmpty, let rowNum = Int(rowPart), rowNum > 0 else { return nil }

        var col = 0
        for char in colPart {
            guard let ascii = char.asciiValue, ascii >= 65, ascii <= 90 else { return nil }
            col = col * 26 + Int(ascii - 65) + 1
        }
        col -= 1  // 0-based

        return CellAddress(column: col, row: rowNum - 1)
    }
}

// MARK: - Cell

struct SpreadsheetCell: Codable, Equatable, Sendable {
    var rawValue: String       // What the user typed (may be formula)
    var isBold: Bool
    var isItalic: Bool
    var alignment: CellAlignment

    init(
        rawValue: String = "",
        isBold: Bool = false,
        isItalic: Bool = false,
        alignment: CellAlignment = .left
    ) {
        self.rawValue = rawValue
        self.isBold = isBold
        self.isItalic = isItalic
        self.alignment = alignment
    }

    var isFormula: Bool {
        rawValue.hasPrefix("=")
    }
}

enum CellAlignment: String, Codable, Sendable {
    case left, center, right
}

// MARK: - Spreadsheet Document

struct SpreadsheetDocument: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var title: String
    var cells: [String: SpreadsheetCell]  // Key: "A1", "B2" etc.
    var columnWidths: [Int: Double]       // Column index → width
    var rowHeights: [Int: Double]         // Row index → height
    var columnCount: Int
    var rowCount: Int
    var createdAt: Date
    var updatedAt: Date
    var isStarred: Bool

    init(
        id: UUID = UUID(),
        title: String = "Untitled Spreadsheet",
        cells: [String: SpreadsheetCell] = [:],
        columnWidths: [Int: Double] = [:],
        rowHeights: [Int: Double] = [:],
        columnCount: Int = 26,
        rowCount: Int = 100,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        isStarred: Bool = false
    ) {
        self.id = id
        self.title = title
        self.cells = cells
        self.columnWidths = columnWidths
        self.rowHeights = rowHeights
        self.columnCount = columnCount
        self.rowCount = rowCount
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.isStarred = isStarred
    }

    func cell(at address: CellAddress) -> SpreadsheetCell {
        cells[address.description] ?? SpreadsheetCell()
    }

    mutating func setCell(at address: CellAddress, value: String) {
        if value.isEmpty {
            cells.removeValue(forKey: address.description)
        } else {
            var cell = cells[address.description] ?? SpreadsheetCell()
            cell.rawValue = value
            cells[address.description] = cell
        }
        updatedAt = Date()
    }

    func columnWidth(for col: Int) -> Double {
        columnWidths[col] ?? 100
    }
}
