//
//  LSPBridgeService.swift
//  MagnetarStudio
//
//  Language Server Protocol bridge service for code intelligence.
//  Communicates with backend LSP server for completion, hover, definition, and references.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "LSPBridge")

// MARK: - LSP Models

/// Supported languages for LSP features
enum LSPLanguage: String, CaseIterable, Sendable {
    case python
    case typescript
    case javascript
    case rust
    case go

    /// Detect language from file extension
    static func from(fileExtension ext: String) -> LSPLanguage? {
        switch ext.lowercased() {
        case "py":
            return .python
        case "ts", "tsx":
            return .typescript
        case "js", "jsx", "mjs", "cjs":
            return .javascript
        case "rs":
            return .rust
        case "go":
            return .go
        default:
            return nil
        }
    }

    /// Detect language from file path
    static func from(filePath: String) -> LSPLanguage? {
        let ext = (filePath as NSString).pathExtension
        return from(fileExtension: ext)
    }
}

/// Position in a text document (0-indexed)
struct LSPPosition: Codable, Sendable, Equatable {
    let line: Int
    let character: Int
}

/// Range in a text document
struct LSPRange: Codable, Sendable, Equatable {
    let start: LSPPosition
    let end: LSPPosition
}

/// Location pointing to a specific range in a file
struct LSPLocation: Codable, Sendable, Identifiable {
    let uri: String
    let range: LSPRange

    var id: String { "\(uri):\(range.start.line):\(range.start.character)" }

    /// Extract file path from URI
    var filePath: String {
        if uri.hasPrefix("file://") {
            return String(uri.dropFirst(7))
        }
        return uri
    }
}

/// Completion item kind (matches LSP spec)
enum LSPCompletionItemKind: Int, Codable, Sendable {
    case text = 1
    case method = 2
    case function = 3
    case constructor = 4
    case field = 5
    case variable = 6
    case classType = 7
    case interface = 8
    case module = 9
    case property = 10
    case unit = 11
    case value = 12
    case enumType = 13
    case keyword = 14
    case snippet = 15
    case color = 16
    case file = 17
    case reference = 18
    case folder = 19
    case enumMember = 20
    case constant = 21
    case structType = 22
    case event = 23
    case `operator` = 24
    case typeParameter = 25

    var iconName: String {
        switch self {
        case .function, .method: return "function"
        case .variable, .field, .property: return "x.squareroot"
        case .classType, .interface, .structType: return "c.square"
        case .module: return "shippingbox"
        case .keyword: return "key"
        case .snippet: return "text.snippet"
        case .constant: return "number"
        case .enumType, .enumMember: return "list.bullet"
        default: return "doc.text"
        }
    }
}

/// A completion item from LSP
struct LSPCompletionItem: Codable, Sendable, Identifiable {
    let label: String
    let kind: LSPCompletionItemKind?
    let detail: String?
    let documentation: String?
    let insertText: String?
    let sortText: String?

    var id: String { label }

    enum CodingKeys: String, CodingKey {
        case label
        case kind
        case detail
        case documentation
        case insertText = "insertText"
        case sortText = "sortText"
    }
}

/// Completion response from backend
struct LSPCompletionResponse: Codable, Sendable {
    let items: [LSPCompletionItem]
}

/// Hover content from LSP
struct LSPHoverContent: Codable, Sendable {
    let kind: String?
    let value: String

    /// Parse markdown or plaintext content
    var displayContent: String {
        value
    }
}

/// Hover response from LSP
struct LSPHoverResponse: Sendable {
    let contents: LSPHoverContent?
    let range: LSPRange?

    var displayContent: String? {
        contents?.displayContent
    }
}

extension LSPHoverResponse: Codable {
    enum CodingKeys: String, CodingKey {
        case contents
        case range
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        range = try container.decodeIfPresent(LSPRange.self, forKey: .range)

        // Contents can be either a string or an object
        if let content = try? container.decode(LSPHoverContent.self, forKey: .contents) {
            contents = content
        } else if let str = try? container.decode(String.self, forKey: .contents) {
            contents = LSPHoverContent(kind: "plaintext", value: str)
        } else {
            contents = nil
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(contents, forKey: .contents)
        try container.encodeIfPresent(range, forKey: .range)
    }
}

/// Diagnostic severity (matches LSP spec)
enum LSPDiagnosticSeverity: Int, Codable, Sendable {
    case error = 1
    case warning = 2
    case information = 3
    case hint = 4

    var iconName: String {
        switch self {
        case .error: return "xmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .information: return "info.circle.fill"
        case .hint: return "lightbulb.fill"
        }
    }

    var color: String {
        switch self {
        case .error: return "red"
        case .warning: return "orange"
        case .information: return "blue"
        case .hint: return "gray"
        }
    }
}

/// A diagnostic message from LSP
struct LSPDiagnostic: Codable, Sendable, Identifiable {
    let range: LSPRange
    let severity: LSPDiagnosticSeverity?
    let code: String?
    let source: String?
    let message: String

    var id: String {
        "\(range.start.line):\(range.start.character):\(message.prefix(20))"
    }
}

/// Diagnostics for a file
struct LSPDiagnosticsResponse: Codable, Sendable {
    let uri: String
    let diagnostics: [LSPDiagnostic]
}

// MARK: - LSP Bridge Service

/// Service for Language Server Protocol features
/// Bridges Swift client to Python backend LSP server
actor LSPBridgeService {
    // MARK: - Singleton

    static let shared = LSPBridgeService()

    // MARK: - Properties

    private let apiClient = ApiClient.shared
    private let basePath = "/v1/lsp"

    /// Cache for recent completions to reduce API calls
    private var completionCache: [String: (items: [LSPCompletionItem], timestamp: Date)] = [:]
    private let cacheTimeout: TimeInterval = 5.0

    // MARK: - Completion

    /// Get code completion suggestions
    /// - Parameters:
    ///   - filePath: Path to the file
    ///   - workspacePath: Root path of the workspace
    ///   - line: Line number (0-indexed)
    ///   - character: Character position (0-indexed)
    ///   - text: Optional file content (sent to server if provided)
    /// - Returns: Array of completion items
    func completion(
        filePath: String,
        workspacePath: String,
        line: Int,
        character: Int,
        text: String? = nil
    ) async throws -> [LSPCompletionItem] {
        guard let language = LSPLanguage.from(filePath: filePath) else {
            logger.debug("[LSP] Unsupported language for file: \(filePath)")
            return []
        }

        // Check cache
        let cacheKey = "\(filePath):\(line):\(character)"
        if let cached = completionCache[cacheKey],
           Date().timeIntervalSince(cached.timestamp) < cacheTimeout {
            return cached.items
        }

        var body: [String: Any] = [
            "language": language.rawValue,
            "workspace_path": workspacePath,
            "file_path": filePath,
            "line": line,
            "character": character
        ]

        if let text = text {
            body["text"] = text
        }

        let response: LSPCompletionResponse = try await apiClient.request(
            path: "\(basePath)/completion",
            method: .post,
            jsonBody: body
        )

        // Update cache
        completionCache[cacheKey] = (response.items, Date())

        logger.debug("[LSP] Got \(response.items.count) completions for \(filePath):\(line):\(character)")
        return response.items
    }

    // MARK: - Hover

    /// Get hover information (type info, documentation)
    /// - Parameters:
    ///   - filePath: Path to the file
    ///   - workspacePath: Root path of the workspace
    ///   - line: Line number (0-indexed)
    ///   - character: Character position (0-indexed)
    /// - Returns: Hover response with content and range
    func hover(
        filePath: String,
        workspacePath: String,
        line: Int,
        character: Int
    ) async throws -> LSPHoverResponse? {
        guard let language = LSPLanguage.from(filePath: filePath) else {
            return nil
        }

        let body: [String: Any] = [
            "language": language.rawValue,
            "workspace_path": workspacePath,
            "file_path": filePath,
            "line": line,
            "character": character
        ]

        let response: LSPHoverResponse = try await apiClient.request(
            path: "\(basePath)/hover",
            method: .post,
            jsonBody: body
        )

        return response
    }

    // MARK: - Go to Definition

    /// Get definition location for a symbol
    /// - Parameters:
    ///   - filePath: Path to the file
    ///   - workspacePath: Root path of the workspace
    ///   - line: Line number (0-indexed)
    ///   - character: Character position (0-indexed)
    /// - Returns: Location of the definition, or nil if not found
    func goToDefinition(
        filePath: String,
        workspacePath: String,
        line: Int,
        character: Int
    ) async throws -> LSPLocation? {
        guard let language = LSPLanguage.from(filePath: filePath) else {
            return nil
        }

        let body: [String: Any] = [
            "language": language.rawValue,
            "workspace_path": workspacePath,
            "file_path": filePath,
            "line": line,
            "character": character
        ]

        // Backend may return single location or array
        struct DefinitionResponse: Codable, Sendable {
            let location: LSPLocation?
            let locations: [LSPLocation]?
        }

        let response: DefinitionResponse = try await apiClient.request(
            path: "\(basePath)/definition",
            method: .post,
            jsonBody: body
        )

        return response.location ?? response.locations?.first
    }

    // MARK: - Find References

    /// Find all references to a symbol
    /// - Parameters:
    ///   - filePath: Path to the file
    ///   - workspacePath: Root path of the workspace
    ///   - line: Line number (0-indexed)
    ///   - character: Character position (0-indexed)
    ///   - includeDeclaration: Whether to include the declaration itself
    /// - Returns: Array of locations where the symbol is referenced
    func findReferences(
        filePath: String,
        workspacePath: String,
        line: Int,
        character: Int,
        includeDeclaration: Bool = true
    ) async throws -> [LSPLocation] {
        guard let language = LSPLanguage.from(filePath: filePath) else {
            return []
        }

        let body: [String: Any] = [
            "language": language.rawValue,
            "workspace_path": workspacePath,
            "file_path": filePath,
            "line": line,
            "character": character,
            "include_declaration": includeDeclaration
        ]

        struct ReferencesResponse: Codable, Sendable {
            let locations: [LSPLocation]
        }

        let response: ReferencesResponse = try await apiClient.request(
            path: "\(basePath)/references",
            method: .post,
            jsonBody: body
        )

        logger.debug("[LSP] Found \(response.locations.count) references")
        return response.locations
    }

    // MARK: - Diagnostics

    /// Get diagnostics for a file
    /// - Parameters:
    ///   - filePath: Path to the file
    ///   - workspacePath: Root path of the workspace
    ///   - text: File content to analyze
    /// - Returns: Array of diagnostics
    func diagnostics(
        filePath: String,
        workspacePath: String,
        text: String
    ) async throws -> [LSPDiagnostic] {
        guard let language = LSPLanguage.from(filePath: filePath) else {
            return []
        }

        let body: [String: Any] = [
            "language": language.rawValue,
            "workspace_path": workspacePath,
            "file_path": filePath,
            "text": text
        ]

        struct DiagnosticsResponse: Codable, Sendable {
            let diagnostics: [LSPDiagnostic]
        }

        let response: DiagnosticsResponse = try await apiClient.request(
            path: "\(basePath)/diagnostics",
            method: .post,
            jsonBody: body
        )

        return response.diagnostics
    }

    // MARK: - Cache Management

    /// Clear the completion cache
    func clearCache() {
        completionCache.removeAll()
    }

    /// Clear expired cache entries
    func pruneCache() {
        let now = Date()
        completionCache = completionCache.filter { _, value in
            now.timeIntervalSince(value.timestamp) < cacheTimeout
        }
    }
}
