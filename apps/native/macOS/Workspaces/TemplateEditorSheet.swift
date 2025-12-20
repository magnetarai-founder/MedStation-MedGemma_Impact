//
//  TemplateEditorSheet.swift
//  MagnetarStudio
//
//  Template editor for creating and editing custom Insights templates
//  Includes prompt engineering guidance and live preview
//

import SwiftUI

struct TemplateEditorSheet: View {
    @Environment(\.dismiss) private var dismiss

    // Template data
    @State private var name: String = ""
    @State private var description: String = ""
    @State private var systemPrompt: String = ""
    @State private var category: TemplateCategory = .general
    @State private var outputFormat: OutputFormat = .markdown

    // UI state
    @State private var isSaving = false
    @State private var error: String?
    @State private var showingPromptTips = false

    // For editing existing template
    let existingTemplate: InsightsTemplate?
    let onSave: () async -> Void

    init(template: InsightsTemplate? = nil, onSave: @escaping () async -> Void = {}) {
        self.existingTemplate = template
        self.onSave = onSave
    }

    var isValid: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty &&
        !systemPrompt.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerBar

            Divider()

            // Content
            HSplitView {
                // Left: Form
                formPane
                    .frame(minWidth: 350, idealWidth: 400)

                // Right: Prompt Editor + Tips
                promptPane
            }

            Divider()

            // Footer with actions
            footerBar
        }
        .frame(width: 900, height: 650)
        .onAppear {
            if let template = existingTemplate {
                loadTemplate(template)
            } else {
                // Start with a helpful template
                systemPrompt = defaultPromptTemplate
            }
        }
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(existingTemplate == nil ? "New Template" : "Edit Template")
                    .font(.headline)
                if let template = existingTemplate {
                    Text("Editing: \(template.name)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            if existingTemplate?.isBuiltin == true {
                Label("Built-in templates cannot be edited", systemImage: "lock.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding()
    }

    // MARK: - Form Pane

    private var formPane: some View {
        Form {
            Section {
                TextField("Template Name", text: $name)
                    .textFieldStyle(.roundedBorder)

                TextField("Description (shown in library)", text: $description)
                    .textFieldStyle(.roundedBorder)
            } header: {
                Text("Template Info")
            }

            Section {
                Picker("Category", selection: $category) {
                    ForEach(TemplateCategory.allCases, id: \.self) { cat in
                        Label(cat.displayName, systemImage: cat.icon)
                            .tag(cat)
                    }
                }

                Picker("Output Format", selection: $outputFormat) {
                    ForEach(OutputFormat.allCases, id: \.self) { format in
                        Text(format.displayName).tag(format)
                    }
                }
            } header: {
                Text("Classification")
            }

            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Available Variables")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    variableReference("{{transcript}}", "Full transcript text")
                    variableReference("{{title}}", "Recording title")
                    variableReference("{{duration}}", "Duration in seconds")
                    variableReference("{{tags}}", "Comma-separated tags")
                    variableReference("{{date}}", "Recording date")
                }
            } header: {
                Text("Template Variables")
            }

            if let error = error {
                Section {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .foregroundStyle(.red)
                }
            }
        }
        .formStyle(.grouped)
        .scrollContentBackground(.hidden)
    }

    private func variableReference(_ variable: String, _ description: String) -> some View {
        HStack {
            Text(variable)
                .font(.system(.caption, design: .monospaced))
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.indigo.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 4))

            Text(description)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Prompt Pane

    private var promptPane: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Prompt header with tips toggle
            HStack {
                Text("System Prompt")
                    .font(.headline)

                Spacer()

                Button(action: { showingPromptTips.toggle() }) {
                    Label(showingPromptTips ? "Hide Tips" : "Show Tips", systemImage: "lightbulb")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.indigo)
            }
            .padding()

            // Tips panel (collapsible)
            if showingPromptTips {
                promptTipsPanel
            }

            // Prompt editor
            TextEditor(text: $systemPrompt)
                .font(.system(.body, design: .monospaced))
                .scrollContentBackground(.hidden)
                .padding(8)
                .background(.background)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(.quaternary, lineWidth: 1)
                )
                .padding(.horizontal)
                .padding(.bottom)

            // Character count
            HStack {
                Spacer()
                Text("\(systemPrompt.count) characters")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal)
            .padding(.bottom, 8)
        }
        .background(.quaternary.opacity(0.3))
    }

    private var promptTipsPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            PromptTip(
                icon: "target",
                title: "Be Specific",
                example: "Extract: chief complaint, symptoms, duration, severity"
            )

            PromptTip(
                icon: "list.bullet.rectangle",
                title: "Define Structure",
                example: "Format as:\n## Section 1\n- Point\n## Section 2\n- Point"
            )

            PromptTip(
                icon: "ruler",
                title: "Set Constraints",
                example: "Keep summary to 3-5 bullet points. Max 200 words."
            )

            PromptTip(
                icon: "doc.text",
                title: "Provide Examples",
                example: "Example output:\n• Main point: [description]\n• Action: [what to do]"
            )

            PromptTip(
                icon: "person.fill.questionmark",
                title: "Define Audience",
                example: "Write for: medical professionals / laypeople / children"
            )
        }
        .padding()
        .background(.indigo.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.horizontal)
        .padding(.bottom, 12)
    }

    // MARK: - Footer

    private var footerBar: some View {
        HStack {
            Button("Cancel") {
                dismiss()
            }
            .keyboardShortcut(.cancelAction)

            Spacer()

            if existingTemplate != nil && existingTemplate?.isBuiltin != true {
                Button("Duplicate as New") {
                    // Clear the existing template reference to create new
                    Task {
                        await saveAsNew()
                    }
                }
            }

            Button(existingTemplate == nil ? "Create Template" : "Save Changes") {
                Task {
                    await saveTemplate()
                }
            }
            .buttonStyle(.borderedProminent)
            .tint(.indigo)
            .disabled(!isValid || isSaving || existingTemplate?.isBuiltin == true)
            .keyboardShortcut(.defaultAction)
        }
        .padding()
    }

    // MARK: - Actions

    private func loadTemplate(_ template: InsightsTemplate) {
        name = template.name
        description = template.description
        systemPrompt = template.systemPrompt
        category = template.category
        outputFormat = template.outputFormat
    }

    private func saveTemplate() async {
        isSaving = true
        error = nil

        do {
            if let existing = existingTemplate, !existing.isBuiltin {
                // Update existing
                try await InsightsService.shared.updateTemplate(
                    templateId: existing.id,
                    name: name.trimmingCharacters(in: .whitespaces),
                    description: description.trimmingCharacters(in: .whitespaces),
                    systemPrompt: systemPrompt,
                    category: category,
                    outputFormat: outputFormat
                )
            } else {
                // Create new
                _ = try await InsightsService.shared.createTemplate(
                    name: name.trimmingCharacters(in: .whitespaces),
                    description: description.trimmingCharacters(in: .whitespaces),
                    systemPrompt: systemPrompt,
                    category: category,
                    outputFormat: outputFormat
                )
            }

            await onSave()
            dismiss()
        } catch {
            self.error = "Failed to save: \(error.localizedDescription)"
        }

        isSaving = false
    }

    private func saveAsNew() async {
        isSaving = true
        error = nil

        do {
            _ = try await InsightsService.shared.createTemplate(
                name: "\(name) (Copy)",
                description: description,
                systemPrompt: systemPrompt,
                category: category,
                outputFormat: outputFormat
            )

            await onSave()
            dismiss()
        } catch {
            self.error = "Failed to create: \(error.localizedDescription)"
        }

        isSaving = false
    }

    // MARK: - Default Template

    private var defaultPromptTemplate: String {
        """
        Analyze the following transcript and provide a structured summary.

        ## Instructions
        - Extract the main topics discussed
        - Identify key points and decisions
        - Note any action items or follow-ups
        - Keep the summary concise but comprehensive

        ## Output Format
        Use markdown formatting with clear headers and bullet points.

        ## Transcript
        {{transcript}}
        """
    }
}

// MARK: - Prompt Tip Component

struct PromptTip: View {
    let icon: String
    let title: String
    let example: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundStyle(.indigo)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.semibold)

                Text(example)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

#Preview {
    TemplateEditorSheet()
}
