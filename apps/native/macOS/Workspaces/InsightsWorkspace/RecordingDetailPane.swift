//
//  RecordingDetailPane.swift
//  MagnetarStudio
//
//  Recording detail view with transcript and outputs for Insights Lab
//  Enhanced with audio controls and word count
//

import SwiftUI
import AppKit

struct RecordingDetailPane: View {
    let recording: InsightsRecording
    let outputs: [FormattedOutput]
    let templates: [InsightsTemplate]
    let onApplyTemplate: (String) async -> Void
    let onDeleteOutput: (String) async -> Void
    let onShowTemplateLibrary: () -> Void
    let onEditTemplate: (InsightsTemplate) -> Void

    @State private var selectedTab = 0
    @State private var isApplying = false
    @State private var showCopiedTranscript = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            recordingHeader

            Divider()

            // Tab selector
            Picker("View", selection: $selectedTab) {
                Text("Transcript").tag(0)
                Text("Outputs (\(outputs.count))").tag(1)
            }
            .pickerStyle(.segmented)
            .padding()

            // Content
            if selectedTab == 0 {
                transcriptView
            } else {
                outputsView
            }
        }
        .background(.background)
    }

    private var recordingHeader: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                // Play button
                Button(action: playRecording) {
                    ZStack {
                        Circle()
                            .fill(Color.indigo)
                            .frame(width: 48, height: 48)

                        Image(systemName: "play.fill")
                            .font(.system(size: 18))
                            .foregroundColor(.white)
                    }
                }
                .buttonStyle(.plain)
                .help("Play recording")

                VStack(alignment: .leading, spacing: 4) {
                    Text(recording.title)
                        .font(.title2)
                        .fontWeight(.semibold)

                    HStack(spacing: 12) {
                        // Duration
                        Label(recording.formattedDuration, systemImage: "clock")

                        // Word count
                        Label(recording.formattedWordCount, systemImage: "text.word.spacing")

                        // Relative date
                        Text("•")
                        Text(recording.relativeDate)
                    }
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                }

                Spacer()

                // Quick actions
                HStack(spacing: 8) {
                    // Share button
                    Button(action: shareRecording) {
                        Image(systemName: "square.and.arrow.up")
                            .font(.system(size: 14))
                            .foregroundColor(.secondary)
                            .frame(width: 32, height: 32)
                            .background(
                                Circle()
                                    .fill(Color(nsColor: .controlBackgroundColor))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Share recording")

                    // Apply template menu
                    Menu {
                        ForEach(templates.filter { $0.isBuiltin }) { template in
                            Button(template.name) {
                                Task {
                                    isApplying = true
                                    await onApplyTemplate(template.id)
                                    isApplying = false
                                }
                            }
                        }
                        Divider()
                        Button("Browse All Templates...") {
                            onShowTemplateLibrary()
                        }
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "doc.badge.plus")
                            Text("Apply Template")
                        }
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color.indigo)
                        .clipShape(Capsule())
                    }
                    .menuStyle(.borderlessButton)
                    .disabled(isApplying)
                }
            }

            // Tags
            if !recording.tags.isEmpty {
                HStack(spacing: 6) {
                    ForEach(recording.tags, id: \.self) { tag in
                        Text(tag)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.indigo.opacity(0.1))
                            .foregroundStyle(.indigo)
                            .clipShape(Capsule())
                    }
                }
            }
        }
        .padding()
    }

    // MARK: - Actions

    private func playRecording() {
        let fileURL = URL(fileURLWithPath: recording.filePath)
        NSWorkspace.shared.open(fileURL)
    }

    private func shareRecording() {
        let fileURL = URL(fileURLWithPath: recording.filePath)
        let items: [Any] = [fileURL, recording.transcript]

        let picker = NSSharingServicePicker(items: items)

        if let window = NSApp.keyWindow,
           let contentView = window.contentView {
            let rect = NSRect(x: contentView.bounds.midX, y: contentView.bounds.midY, width: 1, height: 1)
            picker.show(relativeTo: rect, of: contentView, preferredEdge: .minY)
        }
    }

    private func copyTranscript() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(recording.transcript, forType: .string)

        withAnimation {
            showCopiedTranscript = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation {
                showCopiedTranscript = false
            }
        }
    }

    private var transcriptView: some View {
        VStack(spacing: 0) {
            // Transcript toolbar
            HStack {
                Label(recording.formattedWordCount, systemImage: "text.word.spacing")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                // Copy button
                Button(action: copyTranscript) {
                    HStack(spacing: 4) {
                        Image(systemName: showCopiedTranscript ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 12))
                        Text(showCopiedTranscript ? "Copied!" : "Copy")
                            .font(.caption)
                    }
                    .foregroundColor(showCopiedTranscript ? .green : .secondary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        Capsule()
                            .fill(showCopiedTranscript ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                    )
                }
                .buttonStyle(.plain)
                .help("Copy transcript")
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(.quaternary.opacity(0.2))

            Divider()

            // Transcript content
            ScrollView {
                Text(recording.transcript)
                    .font(.body)
                    .textSelection(.enabled)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private var outputsView: some View {
        Group {
            if outputs.isEmpty {
                VStack(spacing: 16) {
                    Spacer()
                    Image(systemName: "doc.text")
                        .font(.system(size: 40))
                        .foregroundStyle(.tertiary)
                    Text("No Outputs Yet")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("Apply a template to generate formatted output")
                        .font(.subheadline)
                        .foregroundStyle(.tertiary)
                    Button("Browse Templates") {
                        onShowTemplateLibrary()
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.indigo)
                    Spacer()
                }
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(outputs) { output in
                            OutputCard(
                                output: output,
                                templates: templates,
                                onDelete: {
                                    Task { await onDeleteOutput(output.id) }
                                },
                                onRegenerate: {
                                    await onApplyTemplate(output.templateId)
                                },
                                onRefineTemplate: { template in
                                    onEditTemplate(template)
                                }
                            )
                        }
                    }
                    .padding()
                }
            }
        }
    }
}
