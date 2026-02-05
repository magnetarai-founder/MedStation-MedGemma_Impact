//
//  VoicePanel.swift
//  MagnetarStudio
//
//  Voice recording panel with waveform visualization,
//  playback, and transcription display.
//

import SwiftUI
import AVFoundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "VoicePanel")

struct VoicePanel: View {
    @State private var recordings: [VoiceRecording] = []
    @State private var selectedRecordingID: UUID?
    @State private var isRecording = false
    @State private var recordingDuration: TimeInterval = 0
    @State private var audioLevel: Float = 0
    @State private var isPlaying = false
    @State private var playbackProgress: Double = 0
    @State private var isLoading = true
    @State private var transcriptionService = TranscriptionService.shared
    @State private var aiService = WorkspaceAIService.shared
    @StateObject private var recorder = VoiceRecorderManager()

    var body: some View {
        HStack(spacing: 0) {
            // Recordings list
            recordingsList
                .frame(width: 260)

            Divider()

            // Recording / playback area
            if isRecording {
                recordingView
            } else if let recID = selectedRecordingID,
                      let recording = recordings.first(where: { $0.id == recID }) {
                playbackView(recording: recording)
            } else {
                voiceEmptyState
            }
        }
        .task {
            await loadRecordings()
        }
        .onDisappear {
            recorder.stopRecording()
        }
    }

    // MARK: - Recording View

    private var recordingView: some View {
        VStack(spacing: 24) {
            Spacer()

            // Waveform visualization
            WaveformView(audioLevel: audioLevel, isRecording: true)
                .frame(height: 120)
                .padding(.horizontal, 40)

            // Duration
            Text(formatDuration(recordingDuration))
                .font(.system(size: 36, weight: .light, design: .monospaced))
                .foregroundStyle(.primary)

            // Stop button
            Button {
                stopRecording()
            } label: {
                ZStack {
                    Circle()
                        .fill(Color.red)
                        .frame(width: 64, height: 64)

                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.white)
                        .frame(width: 24, height: 24)
                }
            }
            .buttonStyle(.plain)
            .help("Stop Recording")

            Text("Recording...")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Playback View

    private func playbackView(recording: VoiceRecording) -> some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(recording.title)
                        .font(.system(size: 18, weight: .semibold))
                    HStack(spacing: 12) {
                        Text(recording.formattedDuration)
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(.secondary)
                        Text(formatDate(recording.createdAt))
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }
            .padding(16)

            Divider()

            // Waveform / player
            VStack(spacing: 16) {
                WaveformView(audioLevel: 0.3, isRecording: false)
                    .frame(height: 80)
                    .padding(.horizontal, 24)

                // Playback controls
                HStack(spacing: 24) {
                    Button {} label: {
                        Image(systemName: "gobackward.15")
                            .font(.system(size: 20))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)

                    Button {} label: {
                        Image(systemName: isPlaying ? "pause.circle.fill" : "play.circle.fill")
                            .font(.system(size: 48))
                            .foregroundStyle(Color.magnetarPrimary)
                    }
                    .buttonStyle(.plain)

                    Button {} label: {
                        Image(systemName: "goforward.15")
                            .font(.system(size: 20))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.vertical, 24)

            Divider()

            // Transcription
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Transcription")
                            .font(.system(size: 14, weight: .semibold))
                        Spacer()
                        if recording.isTranscribing {
                            ProgressView()
                                .controlSize(.small)
                            Text("Transcribing...")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let transcription = recording.transcription, !transcription.isEmpty {
                        Text(transcription)
                            .font(.system(size: 14))
                            .foregroundStyle(.primary)
                            .textSelection(.enabled)

                        // AI cleanup button
                        HStack(spacing: 8) {
                            Button {
                                cleanUpTranscription(recordingID: recording.id)
                            } label: {
                                Label("Clean Up", systemImage: "sparkles")
                                    .font(.system(size: 11))
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.purple)

                            Button {
                                summarizeTranscription(recordingID: recording.id)
                            } label: {
                                Label("Summarize", systemImage: "text.justify.left")
                                    .font(.system(size: 11))
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.purple)
                        }
                        .padding(.top, 4)
                    } else if !recording.isTranscribing {
                        VStack(spacing: 8) {
                            Text("No transcription available")
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                                .italic()

                            Button {
                                transcribeRecording(recordingID: recording.id)
                            } label: {
                                Label("Transcribe", systemImage: "waveform.badge.magnifyingglass")
                                    .font(.system(size: 12, weight: .medium))
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.small)
                            .tint(.purple)
                        }
                    }
                }
                .padding(16)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color.surfacePrimary)
    }

    // MARK: - Recordings List

    private var recordingsList: some View {
        VStack(spacing: 0) {
            // Header + Record button
            HStack {
                Text("Voice Recordings")
                    .font(.system(size: 13, weight: .semibold))
                Spacer()
                Button {
                    startRecording()
                } label: {
                    HStack(spacing: 4) {
                        Circle()
                            .fill(Color.red)
                            .frame(width: 8, height: 8)
                        Text("Record")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.red.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if recordings.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "waveform")
                        .font(.system(size: 24))
                        .foregroundStyle(.tertiary)
                    Text("No recordings yet")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    Text("Click Record to start")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        ForEach(recordings) { rec in
                            RecordingListRow(
                                recording: rec,
                                isSelected: selectedRecordingID == rec.id,
                                onSelect: { selectedRecordingID = rec.id },
                                onDelete: { deleteRecording(rec) }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceTertiary)
    }

    private var voiceEmptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "waveform")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Record or select a recording")
                .font(.body)
                .foregroundStyle(.secondary)
            Button {
                startRecording()
            } label: {
                HStack(spacing: 6) {
                    Circle()
                        .fill(Color.red)
                        .frame(width: 10, height: 10)
                    Text("Start Recording")
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Recording Actions

    private func startRecording() {
        isRecording = true
        recordingDuration = 0

        let filename = "recording_\(Date().timeIntervalSince1970).m4a"
        let url = Self.storageDir.appendingPathComponent(filename)

        do {
            try recorder.startRecording(to: url) { level in
                audioLevel = level
                recordingDuration += 0.1
            }
        } catch {
            isRecording = false
            logger.error("Failed to start recording: \(error.localizedDescription)")
        }
    }

    private func stopRecording() {
        recorder.stopRecording()
        isRecording = false

        guard let url = recorder.currentURL else { return }

        let recording = VoiceRecording(
            title: "Recording \(recordings.count + 1)",
            fileURL: url,
            duration: recordingDuration
        )

        recordings.insert(recording, at: 0)
        selectedRecordingID = recording.id
        saveMetadata()

        // Auto-transcribe
        transcribeRecording(recordingID: recording.id)
    }

    private func deleteRecording(_ recording: VoiceRecording) {
        recordings.removeAll { $0.id == recording.id }
        if selectedRecordingID == recording.id {
            selectedRecordingID = nil
        }
        PersistenceHelpers.remove(at: recording.fileURL, label: "recording '\(recording.title)'")
        saveMetadata()
    }

    // MARK: - Transcription

    private func transcribeRecording(recordingID: UUID) {
        guard let index = recordings.firstIndex(where: { $0.id == recordingID }) else { return }
        recordings[index].isTranscribing = true
        saveMetadata()

        let url = recordings[index].fileURL

        Task {
            do {
                let text = try await transcriptionService.transcribe(audioURL: url)
                if let i = recordings.firstIndex(where: { $0.id == recordingID }) {
                    recordings[i].transcription = text
                    recordings[i].isTranscribing = false
                    saveMetadata()

                    // Fire automation trigger with completed transcript
                    AutomationTriggerService.shared.recordingStopped(title: recordings[i].title, transcript: text)
                }
            } catch {
                logger.error("Transcription failed: \(error)")
                if let i = recordings.firstIndex(where: { $0.id == recordingID }) {
                    recordings[i].isTranscribing = false
                    saveMetadata()
                }
            }
        }
    }

    private func cleanUpTranscription(recordingID: UUID) {
        guard let index = recordings.firstIndex(where: { $0.id == recordingID }),
              let transcription = recordings[index].transcription else { return }

        let strategy = VoiceAIStrategy()
        Task {
            let cleaned = await aiService.generateSync(
                action: .cleanTranscription,
                input: transcription,
                strategy: strategy
            )
            if !cleaned.isEmpty, let i = recordings.firstIndex(where: { $0.id == recordingID }) {
                recordings[i].transcription = cleaned
                saveMetadata()
            } else if let error = aiService.error {
                logger.warning("AI clean-up failed: \(error)")
            }
        }
    }

    private func summarizeTranscription(recordingID: UUID) {
        guard let index = recordings.firstIndex(where: { $0.id == recordingID }),
              let transcription = recordings[index].transcription else { return }

        let strategy = VoiceAIStrategy()
        Task {
            let summary = await aiService.generateSync(
                action: .summarizeRecording,
                input: transcription,
                strategy: strategy
            )
            if !summary.isEmpty, let i = recordings.firstIndex(where: { $0.id == recordingID }) {
                recordings[i].transcription = "Summary:\n\(summary)\n\nFull Transcription:\n\(transcription)"
                saveMetadata()
            } else if let error = aiService.error {
                logger.warning("AI summarize failed: \(error)")
            }
        }
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio/workspace/voice", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "voice storage")
        return dir
    }

    private static var metadataFile: URL {
        storageDir.appendingPathComponent("_metadata.json")
    }

    private func loadRecordings() async {
        defer { isLoading = false }
        guard let recs = PersistenceHelpers.load([VoiceRecording].self, from: Self.metadataFile, label: "voice recordings") else { return }
        recordings = recs.filter { FileManager.default.fileExists(atPath: $0.fileURL.path) }
            .sorted { $0.createdAt > $1.createdAt }
    }

    private func saveMetadata() {
        PersistenceHelpers.save(recordings, to: Self.metadataFile, label: "voice recordings")
    }

    // MARK: - Formatting

    private func formatDuration(_ interval: TimeInterval) -> String {
        let minutes = Int(interval) / 60
        let seconds = Int(interval) % 60
        let tenths = Int((interval - Double(Int(interval))) * 10)
        return String(format: "%02d:%02d.%d", minutes, seconds, tenths)
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.doesRelativeDateFormatting = true
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

// MARK: - Waveform View

struct WaveformView: View {
    let audioLevel: Float
    let isRecording: Bool

    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 3) {
                ForEach(0..<Int(geometry.size.width / 6), id: \.self) { i in
                    let height = isRecording
                        ? CGFloat.random(in: 0.1...max(0.2, CGFloat(audioLevel)))
                        : CGFloat(sin(Double(i) * 0.3) * 0.3 + 0.4)

                    RoundedRectangle(cornerRadius: 1.5)
                        .fill(isRecording ? Color.red.opacity(0.7) : Color.magnetarPrimary.opacity(0.5))
                        .frame(width: 3, height: geometry.size.height * height)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        }
    }
}

// MARK: - Voice Recorder Manager

class VoiceRecorderManager: ObservableObject {
    private var audioRecorder: AVAudioRecorder?
    private var timer: Timer?
    var currentURL: URL?

    deinit { stopRecording() }

    func startRecording(to url: URL, onLevel: @escaping (Float) -> Void) throws {
        currentURL = url

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.isMeteringEnabled = true
        audioRecorder?.record()

        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.audioRecorder?.updateMeters()
            let level = self?.audioRecorder?.averagePower(forChannel: 0) ?? -160
            // Normalize from dB (-160...0) to 0...1
            let normalized = max(0, (level + 60) / 60)
            DispatchQueue.main.async {
                onLevel(normalized)
            }
        }
    }

    func stopRecording() {
        audioRecorder?.stop()
        audioRecorder = nil
        timer?.invalidate()
        timer = nil
    }
}

// MARK: - Recording List Row

private struct RecordingListRow: View {
    let recording: VoiceRecording
    let isSelected: Bool
    let onSelect: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: "waveform")
                    .font(.system(size: 14))
                    .foregroundStyle(isSelected ? .white : Color.magnetarAccent)
                    .frame(width: 20)

                VStack(alignment: .leading, spacing: 2) {
                    Text(recording.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)

                    HStack(spacing: 8) {
                        Text(recording.formattedDuration)
                            .font(.system(size: 10, design: .monospaced))
                        if recording.transcription != nil {
                            Image(systemName: "text.bubble")
                                .font(.system(size: 9))
                        }
                    }
                    .foregroundStyle(isSelected ? .white.opacity(0.6) : .secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
        .contextMenu {
            Button("Delete", role: .destructive) { onDelete() }
        }
    }
}
