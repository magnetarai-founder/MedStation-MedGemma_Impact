//
//  CodeExplainPopover.swift
//  MagnetarStudio (macOS)
//
//  Right-click context menu "Explain Selection" — shows AI explanation popover.
//  Uses WorkspaceAIService with streaming for progressive display.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeExplain")

struct CodeExplainPopover: View {
    let selectedCode: String
    let language: String
    @Binding var isPresented: Bool

    @State private var explanation = ""
    @State private var isLoading = true
    @State private var streamTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header
            HStack {
                Image(systemName: "lightbulb.fill")
                    .foregroundStyle(.yellow)
                Text("Explanation")
                    .font(.system(size: 12, weight: .semibold))
                Spacer()
                Button {
                    streamTask?.cancel()
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            Divider()

            // Code snippet preview (collapsed)
            Text(String(selectedCode.prefix(100)) + (selectedCode.count > 100 ? "..." : ""))
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.secondary)
                .padding(6)
                .background(RoundedRectangle(cornerRadius: 4).fill(Color.primary.opacity(0.04)))

            // Explanation
            if isLoading && explanation.isEmpty {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.6)
                    Text("Analyzing...")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
            } else {
                ScrollView {
                    Text(explanation)
                        .font(.system(size: 12))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 250)
            }
        }
        .padding(12)
        .frame(width: 380)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .shadow(color: .black.opacity(0.2), radius: 8, y: 4)
        .onAppear { startExplanation() }
        .onDisappear { streamTask?.cancel() }
    }

    private func startExplanation() {
        let aiService = WorkspaceAIService.shared
        let prompt = "Explain this \(language) code concisely:\n\n```\(language)\n\(selectedCode)\n```"

        streamTask = Task { @MainActor in
            let stream = aiService.generate(
                action: .askAI,
                input: prompt,
                strategy: TextAIStrategy()
            )
            for await chunk in stream {
                explanation += chunk
            }
            isLoading = false
        }
    }
}
