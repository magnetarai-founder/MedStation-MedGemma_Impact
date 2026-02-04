import Foundation
import CoreGraphics

/// Document type detected by Vision framework
enum DocumentType: String, Codable, Sendable {
    case letter
    case receipt
    case businessCard
    case form
    case article
    case unknown
}

/// Result from RecognizeDocumentsRequest (iOS 26)
struct DocumentAnalysisResult: Codable, Sendable {
    let documentType: DocumentType
    let boundingBox: CGRect
    let paragraphs: [String]
    let lists: [[String]]
    let tables: [TableStructure]
    let qrCodes: [QRCodeResult]
    let confidence: Float

    init(
        documentType: DocumentType = .unknown,
        boundingBox: CGRect = .zero,
        paragraphs: [String] = [],
        lists: [[String]] = [],
        tables: [TableStructure] = [],
        qrCodes: [QRCodeResult] = [],
        confidence: Float = 0
    ) {
        self.documentType = documentType
        self.boundingBox = boundingBox
        self.paragraphs = paragraphs
        self.lists = lists
        self.tables = tables
        self.qrCodes = qrCodes
        self.confidence = confidence
    }

    /// All text content combined
    var allText: String {
        var parts: [String] = paragraphs
        parts.append(contentsOf: lists.flatMap { $0 })
        parts.append(contentsOf: tables.flatMap { $0.cells.flatMap { row in row.map { $0.text } } })
        return parts.joined(separator: " ")
    }
}

/// Table structure from document recognition
struct TableStructure: Codable, Sendable {
    let rows: Int
    let columns: Int
    let cells: [[DocumentTableCell]]

    init(rows: Int = 0, columns: Int = 0, cells: [[DocumentTableCell]] = []) {
        self.rows = rows
        self.columns = columns
        self.cells = cells
    }
}

/// Individual table cell
struct DocumentTableCell: Codable, Sendable {
    let row: Int
    let column: Int
    let text: String
    let rowSpan: Int
    let columnSpan: Int

    init(row: Int, column: Int, text: String, rowSpan: Int = 1, columnSpan: Int = 1) {
        self.row = row
        self.column = column
        self.text = text
        self.rowSpan = rowSpan
        self.columnSpan = columnSpan
    }
}

/// QR code or barcode result
struct QRCodeResult: Codable, Sendable {
    let payload: String
    let symbology: String
    let boundingBox: CGRect

    init(payload: String, symbology: String, boundingBox: CGRect = .zero) {
        self.payload = payload
        self.symbology = symbology
        self.boundingBox = boundingBox
    }
}

/// OCR text block result
struct RecognizedTextBlock: Codable, Sendable {
    let text: String
    let boundingBox: CGRect
    let confidence: Float
    let language: String?

    init(text: String, boundingBox: CGRect = .zero, confidence: Float = 1.0, language: String? = nil) {
        self.text = text
        self.boundingBox = boundingBox
        self.confidence = confidence
        self.language = language
    }
}

/// Barcode detection result
struct BarcodeResult: Codable, Sendable {
    let payload: String
    let symbology: String
    let boundingBox: CGRect

    init(payload: String, symbology: String, boundingBox: CGRect = .zero) {
        self.payload = payload
        self.symbology = symbology
        self.boundingBox = boundingBox
    }
}
