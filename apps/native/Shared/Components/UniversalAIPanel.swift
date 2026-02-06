//
//  UniversalAIPanel.swift
//  MagnetarStudio
//
//  Universal AI side panel that adapts based on active workspace.
//  Lives in MainAppView's HStack — separate from any individual workspace.
//  Toggled via Header sparkles button or ⇧⌘P.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "UniversalAIPanel")

// MARK: - Universal AI Panel

struct UniversalAIPanel: View {
    @Environment(NavigationStore.self) private var navigationStore
    @State private var aiPanelStore = UniversalAIPanelStore.shared

    var body: some View {
        VStack(spacing: 0) {
            panelHeader
            Divider()
            adaptiveContent
        }
        .background(Color.surfaceSecondary)
    }

    // MARK: - Header

    private var panelHeader: some View {
        HStack {
            Image(systemName: "sparkles")
                .font(.system(size: 12))
                .foregroundStyle(.purple)

            Text("AI")
                .font(.system(size: 13, weight: .semibold))

            Spacer()

            Button {
                aiPanelStore.toggle()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .help("Close AI Panel")
        }
        .padding(.horizontal, 12)
        .frame(height: HubLayout.headerHeight)
    }

    // MARK: - Adaptive Content

    @ViewBuilder
    private var adaptiveContent: some View {
        switch navigationStore.activeWorkspace {
        case .code:
            AIAssistantPanel(codingStore: CodingStore.shared)
        case .workspace:
            HubAIPanelContent()
        case .chat:
            ChatAIHint()
        default:
            GenericAIPanelContent()
        }
    }
}

// MARK: - Hub AI Panel Content

/// Adapts AI based on which Hub panel is selected (Notes/Docs → text, Sheets → formula, Voice → voice).
private struct HubAIPanelContent: View {
    @State private var hubStore = WorkspaceHubStore.shared

    var body: some View {
        switch hubStore.selectedPanel {
        case .notes, .docs, .team:
            TextAIPanelContent()
        case .sheets:
            FormulaAIPanelContent()
        case .voice:
            VoiceAIPanelContent()
        case .pdf, .automations, .plugins:
            GenericAIPanelContent()
        }
    }
}

// MARK: - Text AI Panel Content

/// Writing assistance actions for Notes, Docs, and Team panels.
private struct TextAIPanelContent: View {
    @State private var aiService = WorkspaceAIService.shared
    @State private var selectedAction: WorkspaceAIAction?
    @State private var responseText: String = ""
    @State private var isStreaming: Bool = false
    @State private var customPrompt: String = ""

    private let textStrategy = TextAIStrategy()

    private var textActions: [WorkspaceAIAction] {
        WorkspaceAIAction.allCases.filter { $0.category == .text && $0 != .askAI }
    }

    var body: some View {
        VStack(spacing: 0) {
            if selectedAction == nil {
                actionList
            } else {
                responseView
            }
        }
    }

    // MARK: - Action List

    private var actionList: some View {
        VStack(spacing: 0) {
            ForEach(textActions) { action in
                Button {
                    // Text actions need clipboard/selection content — prompt user
                    selectedAction = action
                    customPrompt = ""
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: action.icon)
                            .frame(width: 20)
                            .foregroundStyle(.purple)
                        Text(action.rawValue)
                            .font(.system(size: 13))
                        Spacer()
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }

            Divider().padding(.vertical, 4)

            // Custom prompt
            HStack(spacing: 8) {
                Image(systemName: "text.bubble")
                    .foregroundStyle(.purple)
                    .frame(width: 20)
                TextField("Ask AI anything...", text: $customPrompt)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13))
                    .onSubmit {
                        guard !customPrompt.isEmpty else { return }
                        startGeneration(action: .askAI, input: customPrompt)
                    }
                if !customPrompt.isEmpty {
                    Button {
                        startGeneration(action: .askAI, input: customPrompt)
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 16))
                            .foregroundStyle(.purple)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)

            Spacer()
        }
        .padding(.vertical, 4)
    }

    // MARK: - Response View

    private var responseView: some View {
        VStack(spacing: 0) {
            // Back button + action name
            HStack {
                Button {
                    selectedAction = nil
                    responseText = ""
                    isStreaming = false
                    aiService.cancel()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 10))
                        Text(selectedAction?.rawValue ?? "Back")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)

            Divider()

            // Text input for the action
            if selectedAction != .askAI && responseText.isEmpty && !isStreaming {
                VStack(spacing: 8) {
                    Text("Paste or type text to \(selectedAction?.rawValue.lowercased() ?? "process"):")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    TextEditor(text: $customPrompt)
                        .font(.system(size: 12))
                        .frame(minHeight: 80, maxHeight: 160)
                        .scrollContentBackground(.hidden)
                        .padding(8)
                        .background(Color.secondary.opacity(0.06))
                        .clipShape(RoundedRectangle(cornerRadius: 6))

                    Button("Generate") {
                        guard !customPrompt.isEmpty, let action = selectedAction else { return }
                        startGeneration(action: action, input: customPrompt)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .tint(.purple)
                    .disabled(customPrompt.isEmpty)
                }
                .padding(14)
            }

            // Streaming response
            if isStreaming || !responseText.isEmpty {
                ScrollView {
                    Text(responseText.isEmpty ? "Thinking..." : responseText)
                        .font(.system(size: 13))
                        .foregroundStyle(responseText.isEmpty ? .secondary : .primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .textSelection(.enabled)
                }

                Divider()

                // Action bar
                HStack(spacing: 8) {
                    if isStreaming {
                        Button("Stop") {
                            aiService.cancel()
                            isStreaming = false
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        ProgressView().controlSize(.small)
                    } else {
                        Button("Copy") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(responseText, forType: .string)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
            }

            Spacer()
        }
    }

    private func startGeneration(action: WorkspaceAIAction, input: String) {
        selectedAction = action
        responseText = ""
        isStreaming = true

        let stream = aiService.generate(
            action: action,
            input: input,
            context: "",
            strategy: textStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
            if responseText.isEmpty, let error = aiService.error {
                responseText = "Error: \(error)"
            }
        }
    }
}

// MARK: - Formula AI Panel Content

/// Formula generation/explanation for Sheets panel.
private struct FormulaAIPanelContent: View {
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
            // Mode toggle
            Picker("", selection: $mode) {
                Text("Generate").tag(FormulaMode.generate)
                Text("Explain").tag(FormulaMode.explain)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)

            Divider()

            // Input
            HStack(spacing: 8) {
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
            .padding(14)

            // Response
            if !responseText.isEmpty || isStreaming {
                Divider()

                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
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

                // Copy formula button
                if !isStreaming, mode == .generate, let formula = sheetsStrategy.parseFormula(responseText) {
                    Divider()
                    HStack {
                        Spacer()
                        Button("Copy Formula") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(formula, forType: .string)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                        .tint(.purple)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                }
            }

            Spacer()
        }
    }

    private func generate() {
        guard !prompt.isEmpty else { return }
        responseText = ""
        isStreaming = true

        let action: WorkspaceAIAction = mode == .generate ? .generateFormula : .explainFormula
        let stream = aiService.generate(
            action: action,
            input: prompt,
            context: "",
            strategy: sheetsStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
            if responseText.isEmpty, let error = aiService.error {
                responseText = "Error: \(error)"
            }
        }
    }
}

// MARK: - Voice AI Panel Content

/// Voice transcription cleanup and summarization.
private struct VoiceAIPanelContent: View {
    @State private var aiService = WorkspaceAIService.shared
    @State private var inputText: String = ""
    @State private var responseText: String = ""
    @State private var isStreaming: Bool = false
    @State private var selectedAction: WorkspaceAIAction?

    private let voiceStrategy = VoiceAIStrategy()

    var body: some View {
        VStack(spacing: 0) {
            // Action buttons
            HStack(spacing: 8) {
                ActionChip(
                    icon: "waveform.badge.magnifyingglass",
                    label: "Clean Up",
                    isSelected: selectedAction == .cleanTranscription
                ) {
                    selectedAction = .cleanTranscription
                }

                ActionChip(
                    icon: "text.justify.left",
                    label: "Summarize",
                    isSelected: selectedAction == .summarizeRecording
                ) {
                    selectedAction = .summarizeRecording
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)

            Divider()

            // Input
            VStack(alignment: .leading, spacing: 6) {
                Text("Paste transcription text:")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                TextEditor(text: $inputText)
                    .font(.system(size: 12))
                    .frame(minHeight: 80, maxHeight: 160)
                    .scrollContentBackground(.hidden)
                    .padding(8)
                    .background(Color.secondary.opacity(0.06))
                    .clipShape(RoundedRectangle(cornerRadius: 6))

                Button("Process") {
                    guard !inputText.isEmpty, let action = selectedAction else { return }
                    startGeneration(action: action)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .tint(.purple)
                .disabled(inputText.isEmpty || selectedAction == nil)
            }
            .padding(14)

            // Response
            if isStreaming || !responseText.isEmpty {
                Divider()

                ScrollView {
                    Text(responseText.isEmpty ? "Thinking..." : responseText)
                        .font(.system(size: 13))
                        .foregroundStyle(responseText.isEmpty ? .secondary : .primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .textSelection(.enabled)
                }

                Divider()

                HStack {
                    if isStreaming {
                        Button("Stop") {
                            aiService.cancel()
                            isStreaming = false
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        ProgressView().controlSize(.small)
                    } else {
                        Button("Copy") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(responseText, forType: .string)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
            }

            Spacer()
        }
    }

    private func startGeneration(action: WorkspaceAIAction) {
        responseText = ""
        isStreaming = true

        let stream = aiService.generate(
            action: action,
            input: inputText,
            context: "",
            strategy: voiceStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
            if responseText.isEmpty, let error = aiService.error {
                responseText = "Error: \(error)"
            }
        }
    }
}

// MARK: - Generic AI Panel Content

/// Simple text AI for Files and other workspaces without specialized strategies.
struct GenericAIPanelContent: View {
    @State private var aiService = WorkspaceAIService.shared
    @State private var prompt: String = ""
    @State private var responseText: String = ""
    @State private var isStreaming: Bool = false

    private let textStrategy = TextAIStrategy()

    var body: some View {
        VStack(spacing: 0) {
            // Input
            HStack(spacing: 8) {
                TextField("Ask AI...", text: $prompt, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13))
                    .lineLimit(1...4)
                    .onSubmit {
                        guard !prompt.isEmpty else { return }
                        startGeneration()
                    }

                Button {
                    startGeneration()
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 20))
                        .foregroundStyle(prompt.isEmpty ? .gray : .purple)
                }
                .buttonStyle(.plain)
                .disabled(prompt.isEmpty || isStreaming)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)

            // Response
            if isStreaming || !responseText.isEmpty {
                Divider()

                ScrollView {
                    Text(responseText.isEmpty ? "Thinking..." : responseText)
                        .font(.system(size: 13))
                        .foregroundStyle(responseText.isEmpty ? .secondary : .primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .textSelection(.enabled)
                }

                Divider()

                HStack {
                    if isStreaming {
                        Button("Stop") {
                            aiService.cancel()
                            isStreaming = false
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                        ProgressView().controlSize(.small)
                    } else if !responseText.isEmpty {
                        Button("Copy") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(responseText, forType: .string)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)

                        Spacer()

                        Button("Clear") {
                            responseText = ""
                            prompt = ""
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
            }

            Spacer()
        }
    }

    private func startGeneration() {
        guard !prompt.isEmpty else { return }
        responseText = ""
        isStreaming = true

        let stream = aiService.generate(
            action: .askAI,
            input: prompt,
            context: "",
            strategy: textStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
            if responseText.isEmpty, let error = aiService.error {
                responseText = "Error: \(error)"
            }
        }
    }
}

// MARK: - Chat AI Hint

/// Static hint shown when Chat workspace is active — Chat is already AI-powered.
private struct ChatAIHint: View {
    var body: some View {
        VStack(spacing: 16) {
            Spacer()

            Image(systemName: "bubble.left.and.bubble.right")
                .font(.system(size: 32))
                .foregroundStyle(.purple.opacity(0.4))

            Text("Chat is AI-Powered")
                .font(.system(size: 14, weight: .semibold))

            Text("Use the chat input below to interact with AI models directly. This panel provides AI assistance for other workspaces.")
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Action Chip (Voice Panel)

private struct ActionChip: View {
    let icon: String
    let label: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11))
                Text(label)
                    .font(.system(size: 12, weight: .medium))
            }
            .foregroundStyle(isSelected ? .white : .purple)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.purple : Color.purple.opacity(0.12))
            )
        }
        .buttonStyle(.plain)
    }
}
