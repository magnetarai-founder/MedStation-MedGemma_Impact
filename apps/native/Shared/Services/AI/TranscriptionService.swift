//
//  TranscriptionService.swift
//  MedStation
//
//  Local speech-to-text transcription using SFSpeechRecognizer.
//  Apple Neural Engine accelerated on macOS 14+.
//

import Foundation
import Speech
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "TranscriptionService")

@MainActor
@Observable
final class TranscriptionService {
    static let shared = TranscriptionService()

    // MARK: - State

    var isAuthorized: Bool = false
    var authorizationStatus: SFSpeechRecognizerAuthorizationStatus = .notDetermined

    private let recognizer: SFSpeechRecognizer?
    private var currentTask: SFSpeechRecognitionTask?

    private init() {
        self.recognizer = SFSpeechRecognizer(locale: Locale.current)
        checkAuthorization()
    }

    // MARK: - Authorization

    func requestAuthorization() {
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            Task { @MainActor [weak self] in
                self?.authorizationStatus = status
                self?.isAuthorized = status == .authorized
                logger.debug("[Transcription] Authorization status: \(String(describing: status))")
            }
        }
    }

    private func checkAuthorization() {
        let status = SFSpeechRecognizer.authorizationStatus()
        authorizationStatus = status
        isAuthorized = status == .authorized
    }

    // MARK: - Transcription

    /// Transcribe an audio file at the given URL.
    /// Returns the transcribed text.
    func transcribe(audioURL: URL) async throws -> String {
        guard let recognizer, recognizer.isAvailable else {
            throw TranscriptionError.recognizerUnavailable
        }

        guard isAuthorized else {
            requestAuthorization()
            throw TranscriptionError.notAuthorized
        }

        guard FileManager.default.fileExists(atPath: audioURL.path) else {
            throw TranscriptionError.fileNotFound
        }

        logger.debug("[Transcription] Starting transcription for: \(audioURL.lastPathComponent)")

        let request = SFSpeechURLRecognitionRequest(url: audioURL)
        request.shouldReportPartialResults = false

        // Cancel any in-flight recognition before starting new one
        currentTask?.cancel()
        currentTask = nil

        return try await withCheckedThrowingContinuation { [weak self] continuation in
            let task = recognizer.recognitionTask(with: request) { result, error in
                if let error {
                    logger.error("[Transcription] Failed: \(error)")
                    continuation.resume(throwing: TranscriptionError.recognitionFailed(error.localizedDescription))
                    return
                }

                guard let result, result.isFinal else { return }

                let text = result.bestTranscription.formattedString
                logger.debug("[Transcription] Complete: \(text.prefix(100))...")
                continuation.resume(returning: text)
            }
            Task { @MainActor in
                self?.currentTask = task
            }
        }
    }
}

// MARK: - Errors

enum TranscriptionError: LocalizedError {
    case recognizerUnavailable
    case notAuthorized
    case fileNotFound
    case recognitionFailed(String)

    var errorDescription: String? {
        switch self {
        case .recognizerUnavailable:
            return "Speech recognition is not available on this device"
        case .notAuthorized:
            return "Speech recognition permission is required. Please enable it in System Settings > Privacy & Security > Speech Recognition."
        case .fileNotFound:
            return "Audio file not found"
        case .recognitionFailed(let reason):
            return "Transcription failed: \(reason)"
        }
    }
}
