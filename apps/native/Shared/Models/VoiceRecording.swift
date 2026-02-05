//
//  VoiceRecording.swift
//  MagnetarStudio
//
//  Metadata model for voice recordings.
//

import Foundation

struct VoiceRecording: Identifiable, Codable, Equatable, Hashable {
    let id: UUID
    var title: String
    var fileURL: URL
    var duration: TimeInterval
    var createdAt: Date
    var transcription: String?
    var isTranscribing: Bool

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

    var formattedDuration: String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}
