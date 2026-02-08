//
//  TemplateEditorView.swift
//  MagnetarStudio (macOS)
//
//  Template editor — presented as sheet from TemplateGalleryView selection.
//

import SwiftUI

struct TemplateEditorView: View {
    @State private var template: WorkspaceTemplate
    let onSave: (WorkspaceTemplate) -> Void
    let onCancel: () -> Void

    @State private var newVariableName = ""

    init(template: WorkspaceTemplate? = nil, onSave: @escaping (WorkspaceTemplate) -> Void, onCancel: @escaping () -> Void) {
        self._template = State(initialValue: template ?? WorkspaceTemplate(name: "My Template"))
        self.onSave = onSave
        self.onCancel = onCancel
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text(template.id == UUID() ? "New Template" : "Edit Template")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
            }
            .padding(16)

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Basic info
                    basicInfoSection

                    Divider()

                    // Target + category
                    targetSection

                    Divider()

                    // Variables
                    variablesSection

                    Divider()

                    // Content
                    contentSection
                }
                .padding(16)
            }

            Divider()

            // Footer
            HStack {
                Spacer()
                Button("Cancel") { onCancel() }
                    .keyboardShortcut(.cancelAction)
                Button("Save Template") {
                    var saved = template
                    saved.updatedAt = Date()
                    onSave(saved)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 520, height: 560)
    }

    // MARK: - Basic Info

    private var basicInfoSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Basic Info")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)

            TextField("Template name", text: $template.name)
                .textFieldStyle(.roundedBorder)

            TextField("Description", text: $template.description)
                .textFieldStyle(.roundedBorder)

            HStack {
                Text("Icon")
                    .font(.system(size: 12))
                TextField("SF Symbol name", text: $template.icon)
                    .textFieldStyle(.roundedBorder)
                Image(systemName: template.icon)
                    .font(.system(size: 16))
                    .foregroundStyle(Color.accentColor)
                    .frame(width: 24)
            }
        }
    }

    // MARK: - Target

    private var targetSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Target")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)

            HStack(spacing: 12) {
                Picker("Panel", selection: $template.targetPanel) {
                    ForEach(TemplateTargetPanel.allCases) { panel in
                        Label(panel.displayName, systemImage: panel.icon).tag(panel)
                    }
                }

                Picker("Category", selection: $template.category) {
                    ForEach(WorkspaceTemplateCategory.allCases) { category in
                        Text(category.rawValue).tag(category)
                    }
                }
            }
        }
    }

    // MARK: - Variables

    private var variablesSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Variables")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)

            Text("Use {{name}} in content to create fill-in fields")
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)

            ForEach(Array(template.variables.enumerated()), id: \.element.id) { index, variable in
                HStack(spacing: 8) {
                    TextField("Name", text: Binding(
                        get: { template.variables[index].name },
                        set: { template.variables[index].name = $0 }
                    ))
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 120)

                    Picker("", selection: Binding(
                        get: { template.variables[index].type },
                        set: { template.variables[index].type = $0 }
                    )) {
                        ForEach(TemplateVariable.VariableType.allCases, id: \.self) { type in
                            Text(type.rawValue.capitalized).tag(type)
                        }
                    }
                    .frame(width: 100)

                    Button {
                        template.variables.remove(at: index)
                    } label: {
                        Image(systemName: "minus.circle")
                            .foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Add variable
            HStack {
                TextField("New variable name", text: $newVariableName)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)

                Button("Add") {
                    guard !newVariableName.isEmpty else { return }
                    template.variables.append(
                        TemplateVariable(name: newVariableName)
                    )
                    newVariableName = ""
                }
                .controlSize(.small)
                .disabled(newVariableName.isEmpty)
            }
        }
    }

    // MARK: - Content

    private var contentSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Content Preview")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)

            if template.targetPanel == .sheet {
                Text("Sheet templates use cell definitions (edit in JSON)")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            } else {
                let blockCount = template.blocks?.count ?? 0
                Text("\(blockCount) blocks defined")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                Text("Tip: Create content in the editor first, then save as template")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
            }
        }
    }
}
