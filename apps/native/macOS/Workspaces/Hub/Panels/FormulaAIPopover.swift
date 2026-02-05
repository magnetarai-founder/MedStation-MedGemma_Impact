//
//  FormulaAIPopover.swift
//  MagnetarStudio
//
//  AI popover for spreadsheet formula generation and explanation.
//  Natural language → formula, or explain existing formula.
//

import SwiftUI

struct FormulaAIPopover: View {
    let selectedCell: CellAddress?
    let onInsertFormula: (String) -> Void
    let onDismiss: () -> Void

    @State private var aiService = WorkspaceAIService.shared
    @State private var prompt: String = ""
    @State private var responseText: String = ""
    @State private var isStreaming: Bool = false
    @State private var mode: FormulaMode = .generate

    private let sheetsStrategy = SheetsAIStrategy()

    enum FormulaMode {
        case generate
        case explain
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header with mode toggle
            header

            Divider()

            // Input
            inputSection

            if !responseText.isEmpty || isStreaming {
                Divider()
                responseSection
            }
        }
        .frame(width: 380)
        .background(Color(nsColor: .windowBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.2), radius: 12, x: 0, y: 4)
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Image(systemName: "sparkles")
                .foregroundStyle(.purple)
            Text("Formula AI")
                .font(.system(size: 13, weight: .semibold))

            Spacer()

            // Mode toggle
            Picker("", selection: $mode) {
                Text("Generate").tag(FormulaMode.generate)
                Text("Explain").tag(FormulaMode.explain)
            }
            .pickerStyle(.segmented)
            .frame(width: 160)

            Button {
                aiService.cancel()
                onDismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }

    // MARK: - Input

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let cell = selectedCell {
                Text("Cell: \(cell.description)")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            HStack {
                TextField(
                    mode == .generate
                        ? "Describe what to calculate..."
                        : "Paste a formula to explain...",
                    text: $prompt
                )
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .onSubmit { generate() }

                Button {
                    generate()
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(.purple)
                }
                .buttonStyle(.plain)
                .disabled(prompt.isEmpty || isStreaming)
            }
        }
        .padding(14)
    }

    // MARK: - Response

    private var responseSection: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    // Formula (if found)
                    if mode == .generate, let formula = sheetsStrategy.parseFormula(responseText) {
                        HStack {
                            Text(formula)
                                .font(.system(size: 13, weight: .medium, design: .monospaced))
                                .foregroundStyle(.purple)
                                .textSelection(.enabled)
                            Spacer()
                        }
                        .padding(10)
                        .background(Color.purple.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }

                    // Explanation text
                    let explanationText = mode == .generate
                        ? sheetsStrategy.parseExplanation(responseText)
                        : responseText
                    if !explanationText.isEmpty {
                        Text(explanationText)
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                            .textSelection(.enabled)
                    } else if isStreaming {
                        Text("Thinking...")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(14)
            }
            .frame(maxHeight: 180)

            // Action buttons
            if !isStreaming, mode == .generate, let formula = sheetsStrategy.parseFormula(responseText) {
                Divider()
                HStack {
                    Spacer()
                    Button("Insert Formula") {
                        onInsertFormula(formula)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .tint(.purple)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
            }
        }
    }

    // MARK: - Generation

    private func generate() {
        guard !prompt.isEmpty else { return }
        responseText = ""
        isStreaming = true

        let action: WorkspaceAIAction = mode == .generate ? .generateFormula : .explainFormula

        let stream = aiService.generate(
            action: action,
            input: prompt,
            context: selectedCell.map { "Selected cell: \($0.description)" } ?? "",
            strategy: sheetsStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
        }
    }
}
