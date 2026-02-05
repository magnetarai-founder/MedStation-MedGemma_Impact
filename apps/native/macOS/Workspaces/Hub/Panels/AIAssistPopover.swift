//
//  AIAssistPopover.swift
//  MagnetarStudio
//
//  Reusable AI assist popover for Notes and Docs panels.
//  Shows streaming AI suggestions with accept/reject actions.
//

import SwiftUI

// MARK: - AI Assist Popover

struct AIAssistPopover: View {
    let inputText: String
    let context: String
    let onAccept: (String) -> Void
    let onDismiss: () -> Void

    @State private var aiService = WorkspaceAIService.shared
    @State private var selectedAction: WorkspaceAIAction?
    @State private var responseText: String = ""
    @State private var isStreaming: Bool = false
    @State private var customPrompt: String = ""

    private let textStrategy = TextAIStrategy()

    private var textActions: [WorkspaceAIAction] {
        WorkspaceAIAction.allCases.filter { $0.category == .text }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            if selectedAction == nil {
                // Action picker
                actionGrid
            } else {
                // Streaming response
                responseView
            }
        }
        .frame(width: 400)
        .background(Color(nsColor: .windowBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.2), radius: 12, x: 0, y: 4)
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Image(systemName: "sparkles")
                .foregroundStyle(.purple)
            Text(selectedAction?.rawValue ?? "AI Assist")
                .font(.system(size: 13, weight: .semibold))

            Spacer()

            if selectedAction != nil {
                Button {
                    selectedAction = nil
                    responseText = ""
                    isStreaming = false
                    aiService.cancel()
                } label: {
                    Image(systemName: "arrow.uturn.backward")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("Back to actions")
            }

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

    // MARK: - Action Grid

    private var actionGrid: some View {
        VStack(spacing: 0) {
            // Quick actions
            ForEach(textActions) { action in
                Button {
                    startGeneration(action: action)
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
                        startGeneration(action: .askAI)
                    }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
        }
        .padding(.vertical, 4)
    }

    // MARK: - Response View

    private var responseView: some View {
        VStack(spacing: 0) {
            // Streaming text
            ScrollView {
                Text(responseText.isEmpty ? "Thinking..." : responseText)
                    .font(.system(size: 13))
                    .foregroundStyle(responseText.isEmpty ? .secondary : .primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(14)
                    .textSelection(.enabled)
            }
            .frame(maxHeight: 250)

            Divider()

            // Action buttons
            HStack(spacing: 8) {
                if isStreaming {
                    Button("Stop") {
                        aiService.cancel()
                        isStreaming = false
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)

                    ProgressView()
                        .controlSize(.small)
                } else if !responseText.isEmpty {
                    Button("Discard") {
                        onDismiss()
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)

                    Spacer()

                    Button("Replace") {
                        onAccept(responseText)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .tint(.purple)
                }

                if !isStreaming {
                    Spacer()
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
        }
    }

    // MARK: - Generation

    private func startGeneration(action: WorkspaceAIAction) {
        selectedAction = action
        responseText = ""
        isStreaming = true

        let input = action == .askAI ? customPrompt : inputText
        let stream = aiService.generate(
            action: action,
            input: input,
            context: context,
            strategy: textStrategy
        )

        Task {
            for await token in stream {
                responseText += token
            }
            isStreaming = false
        }
    }
}
