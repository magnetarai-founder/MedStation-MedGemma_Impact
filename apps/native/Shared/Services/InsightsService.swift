//
//  InsightsService.swift
//  MagnetarStudio
//
//  Service for Insights Lab - Voice recording vault with multi-template outputs
//  One recording -> unlimited formatted outputs via templates
//

import Foundation

// MARK: - Enums

enum TemplateCategory: String, Codable, CaseIterable {
    case general = "GENERAL"
    case medical = "MEDICAL"
    case academic = "ACADEMIC"
    case sermon = "SERMON"
    case meeting = "MEETING"
    case legal = "LEGAL"
    case interview = "INTERVIEW"

    var displayName: String {
        switch self {
        case .general: return "General"
        case .medical: return "Medical"
        case .academic: return "Academic"
        case .sermon: return "Sermon"
        case .meeting: return "Meeting"
        case .legal: return "Legal"
        case .interview: return "Interview"
        }
    }

    var icon: String {
        switch self {
        case .general: return "doc.text"
        case .medical: return "cross.case"
        case .academic: return "graduationcap"
        case .sermon: return "book.closed"
        case .meeting: return "person.3"
        case .legal: return "scale.3d"
        case .interview: return "mic"
        }
    }
}

enum OutputFormat: String, Codable, CaseIterable {
    case markdown = "MARKDOWN"
    case text = "TEXT"
    case json = "JSON"
    case html = "HTML"

    var displayName: String {
        switch self {
        case .markdown: return "Markdown"
        case .text: return "Plain Text"
        case .json: return "JSON"
        case .html: return "HTML"
        }
    }
}

// MARK: - Recording Models

struct InsightsRecording: Codable, Identifiable, Hashable {
    let id: String
    let title: String
    let filePath: String
    let duration: Double
    let transcript: String
    let speakerSegments: [String: AnyCodable]?
    let userId: String
    let teamId: String?
    let folderId: String?
    let tags: [String]
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, title, duration, transcript, tags
        case filePath = "file_path"
        case speakerSegments = "speaker_segments"
        case userId = "user_id"
        case teamId = "team_id"
        case folderId = "folder_id"
        case createdAt = "created_at"
    }

    // Custom Hashable/Equatable ignoring AnyCodable property
    static func == (lhs: InsightsRecording, rhs: InsightsRecording) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    var formattedDuration: String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    var formattedDate: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: createdAt) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        return createdAt
    }
}

struct RecordingListResponse: Codable {
    let recordings: [InsightsRecording]
    let total: Int
}

struct CreateRecordingResponse: Codable {
    let recordingId: String
    let transcript: String
    let duration: Double?
    let message: String

    enum CodingKeys: String, CodingKey {
        case recordingId = "recording_id"
        case transcript, duration, message
    }
}

struct RecordingDetailResponse: Codable {
    let recording: InsightsRecording
    let outputs: [FormattedOutput]
}

// MARK: - Template Models

struct InsightsTemplate: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let description: String
    let systemPrompt: String
    let category: TemplateCategory
    let isBuiltin: Bool
    let outputFormat: OutputFormat
    let createdBy: String
    let teamId: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, name, description, category
        case systemPrompt = "system_prompt"
        case isBuiltin = "is_builtin"
        case outputFormat = "output_format"
        case createdBy = "created_by"
        case teamId = "team_id"
        case createdAt = "created_at"
    }
}

struct TemplateListResponse: Codable {
    let templates: [InsightsTemplate]
    let total: Int
}

struct CreateTemplateResponse: Codable {
    let templateId: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case templateId = "template_id"
        case message
    }
}

// MARK: - Formatted Output Models

struct FormattedOutput: Codable, Identifiable, Hashable {
    let id: String
    let recordingId: String
    let templateId: String
    let templateName: String
    let content: String
    let format: OutputFormat
    let generatedAt: String
    let metadata: [String: AnyCodable]?

    enum CodingKeys: String, CodingKey {
        case id, content, format, metadata
        case recordingId = "recording_id"
        case templateId = "template_id"
        case templateName = "template_name"
        case generatedAt = "generated_at"
    }

    // Custom Hashable/Equatable ignoring AnyCodable property
    static func == (lhs: FormattedOutput, rhs: FormattedOutput) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    var formattedDate: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: generatedAt) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .short
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        return generatedAt
    }
}

struct ApplyTemplateResponse: Codable {
    let outputId: String
    let content: String
    let templateName: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case outputId = "output_id"
        case content
        case templateName = "template_name"
        case message
    }
}

struct BatchApplyResponse: Codable {
    let outputs: [FormattedOutput]
    let totalProcessed: Int
    let failed: Int
    let message: String

    enum CodingKeys: String, CodingKey {
        case outputs, message, failed
        case totalProcessed = "total_processed"
    }
}

// MARK: - Service

@MainActor
class InsightsService {
    static let shared = InsightsService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Recordings

    func listRecordings(folderId: String? = nil) async throws -> [InsightsRecording] {
        var path = "/v1/insights/recordings"
        if let folderId = folderId {
            path += "?folder_id=\(folderId)"
        }
        let response: RecordingListResponse = try await apiClient.request(
            path: path,
            method: .get
        )
        return response.recordings
    }

    func getRecording(recordingId: String) async throws -> RecordingDetailResponse {
        try await apiClient.request(
            path: "/v1/insights/recordings/\(recordingId)",
            method: .get
        )
    }

    func uploadRecording(
        fileURL: URL,
        title: String,
        tags: [String] = [],
        folderId: String? = nil
    ) async throws -> CreateRecordingResponse {
        // Build additional fields for multipart
        var fields: [String: String] = ["title": title]
        if !tags.isEmpty {
            if let tagsData = try? JSONEncoder().encode(tags),
               let tagsString = String(data: tagsData, encoding: .utf8) {
                fields["tags"] = tagsString
            }
        }
        if let folderId = folderId {
            fields["folder_id"] = folderId
        }

        return try await apiClient.multipart(
            path: "/v1/insights/recordings",
            fileField: "audio_file",  // Backend expects "audio_file" not "file"
            fileURL: fileURL,
            parameters: fields
        )
    }

    func updateRecording(
        recordingId: String,
        title: String? = nil,
        tags: [String]? = nil,
        folderId: String? = nil
    ) async throws {
        var jsonBody: [String: Any] = [:]
        if let title = title { jsonBody["title"] = title }
        if let tags = tags { jsonBody["tags"] = tags }
        if let folderId = folderId { jsonBody["folder_id"] = folderId }

        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/insights/recordings/\(recordingId)",
            method: .put,
            jsonBody: jsonBody
        )
    }

    func deleteRecording(recordingId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/insights/recordings/\(recordingId)",
            method: .delete
        )
    }

    // MARK: - Templates

    func listTemplates(category: TemplateCategory? = nil) async throws -> [InsightsTemplate] {
        var path = "/v1/insights/templates"
        if let category = category {
            path += "?category=\(category.rawValue)"
        }
        let response: TemplateListResponse = try await apiClient.request(
            path: path,
            method: .get
        )
        return response.templates
    }

    func createTemplate(
        name: String,
        description: String,
        systemPrompt: String,
        category: TemplateCategory,
        outputFormat: OutputFormat = .markdown
    ) async throws -> CreateTemplateResponse {
        try await apiClient.request(
            path: "/v1/insights/templates",
            method: .post,
            jsonBody: [
                "name": name,
                "description": description,
                "system_prompt": systemPrompt,
                "category": category.rawValue,
                "output_format": outputFormat.rawValue
            ]
        )
    }

    func updateTemplate(
        templateId: String,
        name: String? = nil,
        description: String? = nil,
        systemPrompt: String? = nil,
        category: TemplateCategory? = nil,
        outputFormat: OutputFormat? = nil
    ) async throws {
        var jsonBody: [String: Any] = [:]
        if let name = name { jsonBody["name"] = name }
        if let description = description { jsonBody["description"] = description }
        if let systemPrompt = systemPrompt { jsonBody["system_prompt"] = systemPrompt }
        if let category = category { jsonBody["category"] = category.rawValue }
        if let outputFormat = outputFormat { jsonBody["output_format"] = outputFormat.rawValue }

        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/insights/templates/\(templateId)",
            method: .put,
            jsonBody: jsonBody
        )
    }

    func deleteTemplate(templateId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/insights/templates/\(templateId)",
            method: .delete
        )
    }

    // MARK: - Template Application

    func applyTemplate(
        recordingId: String,
        templateId: String
    ) async throws -> ApplyTemplateResponse {
        try await apiClient.request(
            path: "/v1/insights/recordings/\(recordingId)/apply-template",
            method: .post,
            jsonBody: ["template_id": templateId]
        )
    }

    func batchApplyTemplates(
        recordingIds: [String],
        templateIds: [String]
    ) async throws -> BatchApplyResponse {
        try await apiClient.request(
            path: "/v1/insights/recordings/batch-apply",
            method: .post,
            jsonBody: [
                "recording_ids": recordingIds,
                "template_ids": templateIds
            ]
        )
    }

    func getOutputs(recordingId: String) async throws -> [FormattedOutput] {
        let response: [String: [FormattedOutput]] = try await apiClient.request(
            path: "/v1/insights/recordings/\(recordingId)/outputs",
            method: .get
        )
        return response["outputs"] ?? []
    }

    func deleteOutput(outputId: String) async throws {
        let _: EmptyResponse = try await apiClient.request(
            path: "/v1/insights/outputs/\(outputId)",
            method: .delete
        )
    }
}
