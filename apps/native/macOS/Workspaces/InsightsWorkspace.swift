//
//  InsightsWorkspace.swift
//  MagnetarStudio
//
//  Insights Lab - Voice recording vault with multi-template outputs
//  One recording -> unlimited formatted outputs via templates
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
        async let recordingsTask = loadRecordings()
        async let templatesTask = loadTemplates()
        await recordingsTask
        await templatesTask
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
            let response = try await service.applyTemplate(recordingId: recordingId, templateId: templateId)
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

// MARK: - Recording Row

struct RecordingRow: View {
    let recording: InsightsRecording
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            // Waveform icon
            Image(systemName: "waveform")
                .font(.title2)
                .foregroundStyle(isSelected ? .white : .indigo)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 4) {
                Text(recording.title)
                    .font(.headline)
                    .lineLimit(1)
                    .foregroundStyle(isSelected ? .white : .primary)

                HStack(spacing: 8) {
                    Label(recording.formattedDuration, systemImage: "clock")
                        .font(.caption)
                    Text(recording.formattedDate)
                        .font(.caption)
                }
                .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)

                if !recording.tags.isEmpty {
                    HStack(spacing: 4) {
                        ForEach(recording.tags.prefix(3), id: \.self) { tag in
                            Text(tag)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(isSelected ? .white.opacity(0.2) : .indigo.opacity(0.1))
                                .clipShape(Capsule())
                        }
                    }
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(isSelected ? .white.opacity(0.6) : Color.secondary.opacity(0.5))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(isSelected ? Color.indigo : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.horizontal, 8)
    }
}

// MARK: - Recording Detail Pane

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

// MARK: - Output Card

struct OutputCard: View {
    let output: FormattedOutput
    let templates: [InsightsTemplate]
    let onDelete: () -> Void
    let onRegenerate: () async -> Void
    let onRefineTemplate: (InsightsTemplate) -> Void

    @State private var isExpanded = true
    @State private var isRegenerating = false

    var outputTemplate: InsightsTemplate? {
        templates.first { $0.id == output.templateId }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "doc.text.fill")
                    .foregroundStyle(.indigo)
                Text(output.templateName)
                    .font(.headline)
                Spacer()
                Text(output.formattedDate)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                // Regenerate button
                Button(action: {
                    Task {
                        isRegenerating = true
                        await onRegenerate()
                        isRegenerating = false
                    }
                }) {
                    if isRegenerating {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                .buttonStyle(.plain)
                .help("Regenerate with same template")
                .disabled(isRegenerating)

                Button(action: { isExpanded.toggle() }) {
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                }
                .buttonStyle(.plain)

                Menu {
                    Button("Copy Content") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(output.content, forType: .string)
                    }

                    if let template = outputTemplate, !template.isBuiltin {
                        Button("Refine Template...") {
                            onRefineTemplate(template)
                        }
                    }

                    Button("Export as Markdown...") {
                        exportAsMarkdown()
                    }

                    Divider()
                    Button("Delete", role: .destructive, action: onDelete)
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
                .menuStyle(.borderlessButton)
            }
            .padding()
            .background(.quaternary.opacity(0.3))

            if isExpanded {
                Divider()

                // Content
                ScrollView {
                    Text(output.content)
                        .font(.body)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                }
                .frame(maxHeight: 400)
            }
        }
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(.quaternary, lineWidth: 1)
        )
    }

    private func exportAsMarkdown() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.text]
        panel.nameFieldStringValue = "\(output.templateName).md"

        if panel.runModal() == .OK, let url = panel.url {
            try? output.content.write(to: url, atomically: true, encoding: .utf8)
        }
    }
}

// MARK: - Upload Recording Sheet

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

// MARK: - Template Library Sheet

struct TemplateLibrarySheet: View {
    let templates: [InsightsTemplate]
    let onApply: (String) async -> Void
    let onRefresh: () async -> Void
    let onEditTemplate: (InsightsTemplate?) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var selectedCategory: TemplateCategory?
    @State private var searchText = ""

    var filteredTemplates: [InsightsTemplate] {
        var result = templates
        if let category = selectedCategory {
            result = result.filter { $0.category == category }
        }
        if !searchText.isEmpty {
            result = result.filter {
                $0.name.localizedCaseInsensitiveContains(searchText) ||
                $0.description.localizedCaseInsensitiveContains(searchText)
            }
        }
        return result
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Template Library")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button(action: {
                    onEditTemplate(nil)
                }) {
                    Label("New Template", systemImage: "plus.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)

                Button("Done") { dismiss() }
            }
            .padding()

            Divider()

            HStack(spacing: 0) {
                // Categories sidebar
                VStack(alignment: .leading, spacing: 4) {
                    Text("Categories")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.top, 8)

                    Button(action: { selectedCategory = nil }) {
                        HStack {
                            Text("All Templates")
                            Spacer()
                            Text("\(templates.count)")
                                .foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(selectedCategory == nil ? .indigo.opacity(0.1) : .clear)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)

                    ForEach(TemplateCategory.allCases, id: \.self) { category in
                        let count = templates.filter { $0.category == category }.count
                        if count > 0 {
                            Button(action: { selectedCategory = category }) {
                                HStack {
                                    Image(systemName: category.icon)
                                        .frame(width: 20)
                                    Text(category.displayName)
                                    Spacer()
                                    Text("\(count)")
                                        .foregroundStyle(.secondary)
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(selectedCategory == category ? .indigo.opacity(0.1) : .clear)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    Spacer()
                }
                .frame(width: 180)
                .padding(.vertical, 8)

                Divider()

                // Templates grid
                VStack(spacing: 0) {
                    // Search
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                        TextField("Search templates...", text: $searchText)
                            .textFieldStyle(.plain)
                    }
                    .padding(8)
                    .background(.quaternary.opacity(0.5))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .padding()

                    ScrollView {
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 240))], spacing: 12) {
                            ForEach(filteredTemplates) { template in
                                TemplateCard(
                                    template: template,
                                    onApply: {
                                        Task {
                                            await onApply(template.id)
                                            dismiss()
                                        }
                                    },
                                    onEdit: {
                                        onEditTemplate(template)
                                    },
                                    onDelete: {
                                        Task {
                                            try? await InsightsService.shared.deleteTemplate(templateId: template.id)
                                            await onRefresh()
                                        }
                                    }
                                )
                            }
                        }
                        .padding()
                    }
                }
            }
        }
        .frame(width: 800, height: 550)
    }
}

// MARK: - Template Card

struct TemplateCard: View {
    let template: InsightsTemplate
    let onApply: () -> Void
    let onEdit: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var categoryColor: Color {
        switch template.category {
        case .general: return .blue
        case .medical: return .red
        case .academic: return .purple
        case .sermon: return .orange
        case .meeting: return .green
        case .legal: return .gray
        case .interview: return .pink
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                // Category badge
                Text(template.category.displayName)
                    .font(.caption2)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(categoryColor.opacity(0.15))
                    .foregroundStyle(categoryColor)
                    .clipShape(RoundedRectangle(cornerRadius: 4))

                Spacer()

                if template.isBuiltin {
                    Image(systemName: "lock.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .help("Built-in template (cannot edit)")
                }
            }

            Text(template.name)
                .font(.headline)
                .lineLimit(1)

            Text(template.description)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(2)

            Spacer()

            HStack(spacing: 8) {
                Button("Apply") {
                    onApply()
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)
                .controlSize(.small)

                Spacer()

                if !template.isBuiltin {
                    Button(action: onEdit) {
                        Image(systemName: "pencil")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                    .help("Edit template")

                    Button(action: onDelete) {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.red.opacity(0.7))
                    .help("Delete template")
                }
            }
        }
        .padding()
        .frame(height: 140)
        .background(isHovered ? Color.gray.opacity(0.1) : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? Color.indigo.opacity(0.3) : Color.gray.opacity(0.2), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

#Preview {
    InsightsWorkspace()
        .frame(width: 1200, height: 800)
}
