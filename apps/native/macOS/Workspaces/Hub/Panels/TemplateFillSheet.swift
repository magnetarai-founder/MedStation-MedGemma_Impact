//
//  TemplateFillSheet.swift
//  MagnetarStudio (macOS)
//
//  Form to fill in template variables before instantiation.
//  Type-aware inputs: text field, number stepper, date picker, dropdown.
//

import SwiftUI

struct TemplateFillSheet: View {
    let template: WorkspaceTemplate
    let onConfirm: (String, [String: String]) -> Void  // (title, variables)
    let onCancel: () -> Void

    @State private var title: String = ""
    @State private var variableValues: [String: String] = [:]

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 10) {
                Image(systemName: template.icon)
                    .font(.system(size: 16))
                    .foregroundStyle(Color.accentColor)

                VStack(alignment: .leading, spacing: 2) {
                    Text(template.name)
                        .font(.system(size: 14, weight: .semibold))
                    Text(template.description)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer()
            }
            .padding(16)

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Title field
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Title")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)
                        TextField(template.name, text: $title)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 13))
                    }

                    if !template.variables.isEmpty {
                        Divider()

                        Text("Template Fields")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)

                        ForEach(template.variables) { variable in
                            variableField(variable)
                        }
                    }
                }
                .padding(16)
            }

            Divider()

            // Footer
            HStack {
                Spacer()
                Button("Cancel") { onCancel() }
                    .keyboardShortcut(.cancelAction)
                Button("Create") {
                    let finalTitle = title.isEmpty ? template.name : title
                    onConfirm(finalTitle, variableValues)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 400, height: min(CGFloat(200 + template.variables.count * 60), 500))
        .onAppear {
            title = template.name
            for variable in template.variables {
                variableValues[variable.name] = ""
            }
        }
    }

    // MARK: - Variable Fields

    @ViewBuilder
    private func variableField(_ variable: TemplateVariable) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(variable.name.capitalized)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            switch variable.type {
            case .text:
                TextField(variable.placeholder, text: binding(for: variable.name))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 13))

            case .number:
                TextField(variable.placeholder, text: binding(for: variable.name))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 13))

            case .date:
                HStack {
                    TextField("YYYY-MM-DD", text: binding(for: variable.name))
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 13))

                    Button("Today") {
                        let formatter = DateFormatter()
                        formatter.dateFormat = "yyyy-MM-dd"
                        variableValues[variable.name] = formatter.string(from: Date())
                    }
                    .controlSize(.small)
                }

            case .choice:
                if let choices = variable.choices, !choices.isEmpty {
                    Picker("", selection: binding(for: variable.name)) {
                        Text("Select...").tag("")
                        ForEach(choices, id: \.self) { choice in
                            Text(choice).tag(choice)
                        }
                    }
                    .labelsHidden()
                } else {
                    TextField(variable.placeholder, text: binding(for: variable.name))
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 13))
                }
            }
        }
    }

    private func binding(for key: String) -> Binding<String> {
        Binding(
            get: { variableValues[key] ?? "" },
            set: { variableValues[key] = $0 }
        )
    }
}
