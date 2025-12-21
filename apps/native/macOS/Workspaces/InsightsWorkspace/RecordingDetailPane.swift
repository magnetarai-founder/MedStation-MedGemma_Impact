//
//  RecordingDetailPane.swift
//  MagnetarStudio
//
//  Recording detail view with transcript and outputs for Insights Lab
//

import SwiftUI

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
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(recording.title)
                        .font(.title2)
                        .fontWeight(.semibold)

                    HStack(spacing: 16) {
                        Label(recording.formattedDuration, systemImage: "clock")
                        Label(recording.formattedDate, systemImage: "calendar")
                    }
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                }

                Spacer()

                // Quick apply buttons
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
                    Label("Apply Template", systemImage: "doc.badge.plus")
                }
                .menuStyle(.borderlessButton)
                .disabled(isApplying)
            }

            if !recording.tags.isEmpty {
                HStack(spacing: 6) {
                    ForEach(recording.tags, id: \.self) { tag in
                        Text(tag)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.indigo.opacity(0.1))
                            .clipShape(Capsule())
                    }
                }
            }
        }
        .padding()
    }

    private var transcriptView: some View {
        ScrollView {
            Text(recording.transcript)
                .font(.body)
                .textSelection(.enabled)
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
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
