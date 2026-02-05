//
//  VoiceRecording.swift
//  MagnetarStudio
//
//  Metadata model for voice recordings.
//

import Foundation

struct VoiceRecording: Identifiable, Codable, Equatable, Hashable, Sendable {
    let id: UUID
    var title: String
    var fileURL: URL
    var duration: TimeInterval
    var createdAt: Date
    var transcription: String?
    var isTranscribing: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, fileURL, duration, createdAt, transcription
    }

    init(
        id: UUID = UUID(),
        title: String = "Recording",
        fileURL: URL,
        duration: TimeInterval = 0,
        createdAt: Date = Date(),
        transcription: String? = nil,
        isTranscribing: Bool = false
    ) {
        self.id = id
        self.title = title
        self.fileURL = fileURL
        self.duration = duration
        self.createdAt = createdAt
        self.transcription = transcription
        self.isTranscribing = isTranscribing
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        fileURL = try container.decode(URL.self, forKey: .fileURL)
        duration = try container.decode(TimeInterval.self, forKey: .duration)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        transcription = try container.decodeIfPresent(String.self, forKey: .transcription)
        isTranscribing = false
    }

    var formattedDuration: String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}
