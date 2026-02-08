//
//  DetachedNoteWindow.swift
//  MagnetarStudio (macOS)
//
//  A standalone note window opened from Quick Action menu
//  Provides a focused writing experience with the block-based editor
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DetachedNoteWindow")

struct DetachedNoteWindow: View {
    @State private var noteTitle = "Untitled"
    @State private var noteContent = ""
    @State private var isEditing = false
    @State private var lastSaved: Date?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Editor
            WorkspaceEditor(content: $noteContent)
                .onChange(of: noteContent) { _, _ in
                    // Auto-save indicator
                    lastSaved = Date()
                }
        }
        .frame(minWidth: 500, minHeight: 400)
        .background(Color(NSColor.windowBackgroundColor))
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: 12) {
            // Editable title
            if isEditing {
                TextField("Note title", text: $noteTitle)
                    .textFieldStyle(.plain)
                    .font(.system(size: 16, weight: .semibold))
                    .onSubmit {
                        isEditing = false
                    }
            } else {
                Text(noteTitle)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(.primary)
                    .onTapGesture(count: 2) {
                        isEditing = true
                    }
            }

            Spacer()

            // Save status
            if let saved = lastSaved {
                Text("Saved \(formatTimestamp(saved))")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            // Slash command hint
            Text("Type / for commands")
                .font(.system(size: 11))
                .foregroundStyle(.secondary.opacity(0.6))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.gray.opacity(0.1))
                )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    // MARK: - Helpers

    private func formatTimestamp(_ date: Date) -> String {
        let diff = Date().timeIntervalSince(date)
        if diff < 5 { return "just now" }
        else if diff < 60 { return "\(Int(diff))s ago" }
        else if diff < 3600 { return "\(Int(diff / 60))m ago" }
        else { return "\(Int(diff / 3600))h ago" }
    }
}

#Preview {
    DetachedNoteWindow()
        .frame(width: 700, height: 500)
}
