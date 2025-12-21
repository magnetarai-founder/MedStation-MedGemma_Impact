//
//  UploadRecordingSheet.swift
//  MagnetarStudio
//
//  Upload recording sheet for Insights Lab
//

import SwiftUI
import UniformTypeIdentifiers
import AppKit

struct UploadRecordingSheet: View {
    let onUpload: (URL, String, [String]) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedFile: URL?
    @State private var title = ""
    @State private var tagsText = ""
    @State private var isUploading = false

    var body: some View {
        VStack(spacing: 20) {
            Text("Upload Recording")
                .font(.title2)
                .fontWeight(.semibold)

            // File picker
            VStack(spacing: 8) {
                if let file = selectedFile {
                    HStack {
                        Image(systemName: "waveform")
                            .foregroundStyle(.indigo)
                        Text(file.lastPathComponent)
                            .lineLimit(1)
                        Spacer()
                        Button("Change") {
                            pickFile()
                        }
                    }
                    .padding()
                    .background(.quaternary.opacity(0.5))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                } else {
                    Button(action: pickFile) {
                        VStack(spacing: 12) {
                            Image(systemName: "arrow.up.doc")
                                .font(.largeTitle)
                            Text("Select Audio File")
                                .font(.headline)
                            Text("M4A, MP3, WAV, or other audio formats")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                        .background(.quaternary.opacity(0.3))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(style: StrokeStyle(lineWidth: 2, dash: [8]))
                                .foregroundStyle(.quaternary)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }

            // Title
            TextField("Title", text: $title)
                .textFieldStyle(.roundedBorder)

            // Tags
            TextField("Tags (comma-separated)", text: $tagsText)
                .textFieldStyle(.roundedBorder)

            Spacer()

            // Actions
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button("Upload") {
                    Task {
                        guard let file = selectedFile else { return }
                        isUploading = true
                        let tags = tagsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
                        await onUpload(file, title.isEmpty ? file.lastPathComponent : title, tags)
                        isUploading = false
                        dismiss()
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)
                .disabled(selectedFile == nil || isUploading)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(24)
        .frame(width: 480, height: 400)
    }

    private func pickFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.audio, .mpeg4Audio, .mp3, .wav, .aiff]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        if panel.runModal() == .OK {
            selectedFile = panel.url
            if title.isEmpty, let url = panel.url {
                title = url.deletingPathExtension().lastPathComponent
            }
        }
    }
}
