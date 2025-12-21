//
//  InsightsWorkspace.swift
//  MagnetarStudio
//
//  Insights Lab - Voice recording vault with multi-template outputs
//  One recording -> unlimited formatted outputs via templates
//
//  This file has been refactored into InsightsWorkspace/ folder:
//  - RecordingRow.swift: Recording list item
//  - RecordingDetailPane.swift: Detail view with transcript and outputs
//  - OutputCard.swift: Formatted output card
//  - UploadRecordingSheet.swift: Upload recording sheet
//  - TemplateLibrarySheet.swift: Template library sheet
//  - TemplateCard.swift: Template card
//

import SwiftUI
import UniformTypeIdentifiers

struct InsightsWorkspace: View {
    @State private var recordings: [InsightsRecording] = []
    @State private var templates: [InsightsTemplate] = []
    @State private var selectedRecording: InsightsRecording?
    @State private var selectedOutputs: [FormattedOutput] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var showUploadSheet = false
    @State private var showTemplateLibrary = false
    @State private var showTemplateEditor = false
    @State private var templateToEdit: InsightsTemplate?
    @State private var searchText = ""

    private let service = InsightsService.shared

    var filteredRecordings: [InsightsRecording] {
        if searchText.isEmpty {
            return recordings
        }
        return recordings.filter {
            $0.title.localizedCaseInsensitiveContains(searchText) ||
            $0.tags.contains { $0.localizedCaseInsensitiveContains(searchText) }
        }
    }

    var body: some View {
        HSplitView {
            // Left: Recordings List
            recordingsPane
                .frame(minWidth: 280, idealWidth: 320, maxWidth: 400)

            // Right: Recording Detail with Outputs
            detailPane
        }
        .task {
            await loadData()
        }
        .sheet(isPresented: $showUploadSheet) {
            UploadRecordingSheet(onUpload: { fileURL, title, tags in
                await uploadRecording(fileURL: fileURL, title: title, tags: tags)
            })
        }
        .sheet(isPresented: $showTemplateLibrary) {
            TemplateLibrarySheet(
                templates: templates,
                onApply: { templateId in
                    if let recording = selectedRecording {
                        await applyTemplate(recordingId: recording.id, templateId: templateId)
                    }
                },
                onRefresh: {
                    await loadTemplates()
                },
                onEditTemplate: { template in
                    templateToEdit = template
                    showTemplateLibrary = false
                    showTemplateEditor = true
                }
            )
        }
        .sheet(isPresented: $showTemplateEditor) {
            TemplateEditorSheet(
                template: templateToEdit,
                onSave: {
                    await loadTemplates()
                    templateToEdit = nil
                }
            )
        }
    }

    // MARK: - Recordings Pane

    private var recordingsPane: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Recordings")
                    .font(.headline)
                Spacer()
                Button(action: { showUploadSheet = true }) {
                    Image(systemName: "plus.circle.fill")
                        .foregroundStyle(.indigo)
                }
                .buttonStyle(.plain)
                .help("Upload Recording")
            }
            .padding()

            // Search
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search recordings...", text: $searchText)
                    .textFieldStyle(.plain)
            }
            .padding(8)
            .background(.quaternary.opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal)
            .padding(.bottom, 8)

            Divider()

            // Recordings List
            if isLoading && recordings.isEmpty {
                Spacer()
                ProgressView()
                    .progressViewStyle(.circular)
                Spacer()
            } else if recordings.isEmpty {
                emptyRecordingsView
            } else {
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(filteredRecordings) { recording in
                            RecordingRow(
                                recording: recording,
                                isSelected: selectedRecording?.id == recording.id
                            )
                            .onTapGesture {
                                selectRecording(recording)
                            }
                            .contextMenu {
                                Button("Delete", role: .destructive) {
                                    Task { await deleteRecording(recording) }
                                }
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(.background)
    }

    private var emptyRecordingsView: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "waveform.circle")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("No Recordings Yet")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Upload an audio file to get started")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
            Button("Upload Recording") {
                showUploadSheet = true
            }
            .buttonStyle(.borderedProminent)
            .tint(.indigo)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Detail Pane

    private var detailPane: some View {
        Group {
            if let recording = selectedRecording {
                RecordingDetailPane(
                    recording: recording,
                    outputs: selectedOutputs,
                    templates: templates,
                    onApplyTemplate: { templateId in
                        await applyTemplate(recordingId: recording.id, templateId: templateId)
                    },
                    onDeleteOutput: { outputId in
                        await deleteOutput(outputId)
                    },
                    onShowTemplateLibrary: {
                        showTemplateLibrary = true
                    },
                    onEditTemplate: { template in
                        templateToEdit = template
                        showTemplateEditor = true
                    }
                )
            } else {
                emptyDetailView
            }
        }
    }

    private var emptyDetailView: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Select a Recording")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Choose a recording to view its transcript and outputs")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.background)
    }

    // MARK: - Data Operations

    private func loadData() async {
        isLoading = true
        async let recordingsLoad: () = loadRecordings()
        async let templatesLoad: () = loadTemplates()
        _ = await (recordingsLoad, templatesLoad)
        isLoading = false
    }

    private func loadRecordings() async {
        do {
            recordings = try await service.listRecordings()
        } catch {
            self.error = "Failed to load recordings: \(error.localizedDescription)"
        }
    }

    private func loadTemplates() async {
        do {
            templates = try await service.listTemplates()
        } catch {
            self.error = "Failed to load templates: \(error.localizedDescription)"
        }
    }

    private func selectRecording(_ recording: InsightsRecording) {
        selectedRecording = recording
        Task {
            do {
                let detail = try await service.getRecording(recordingId: recording.id)
                selectedOutputs = detail.outputs
            } catch {
                self.error = "Failed to load outputs: \(error.localizedDescription)"
            }
        }
    }

    private func uploadRecording(fileURL: URL, title: String, tags: [String]) async {
        do {
            _ = try await service.uploadRecording(fileURL: fileURL, title: title, tags: tags)
            await loadRecordings()
            showUploadSheet = false
        } catch {
            self.error = "Upload failed: \(error.localizedDescription)"
        }
    }

    private func deleteRecording(_ recording: InsightsRecording) async {
        do {
            try await service.deleteRecording(recordingId: recording.id)
            recordings.removeAll { $0.id == recording.id }
            if selectedRecording?.id == recording.id {
                selectedRecording = nil
                selectedOutputs = []
            }
        } catch {
            self.error = "Delete failed: \(error.localizedDescription)"
        }
    }

    private func applyTemplate(recordingId: String, templateId: String) async {
        do {
            _ = try await service.applyTemplate(recordingId: recordingId, templateId: templateId)
            // Reload outputs
            let detail = try await service.getRecording(recordingId: recordingId)
            selectedOutputs = detail.outputs
        } catch {
            self.error = "Apply template failed: \(error.localizedDescription)"
        }
    }

    private func deleteOutput(_ outputId: String) async {
        do {
            try await service.deleteOutput(outputId: outputId)
            selectedOutputs.removeAll { $0.id == outputId }
        } catch {
            self.error = "Delete output failed: \(error.localizedDescription)"
        }
    }
}

#Preview {
    InsightsWorkspace()
        .frame(width: 1200, height: 800)
}
