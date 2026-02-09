//
//  DocsToolbar.swift
//  MagnetarStudio
//
//  Toolbar for the Docs panel.
//  Sidebar toggle, AI assist, star, export, and more options.
//

import SwiftUI

struct DocsToolbar: View {
    @Binding var document: WorkspaceDocument
    @Binding var showDocsList: Bool
    @State private var showAIAssist = false
    @State private var showExport = false

    var body: some View {
        HStack(spacing: 4) {
            // Toggle docs list
            Button {
                withAnimation(.magnetarQuick) {
                    showDocsList.toggle()
                }
            } label: {
                Image(systemName: showDocsList ? "sidebar.left" : "sidebar.left")
                    .font(.system(size: 13))
                    .foregroundStyle(showDocsList ? .primary : .secondary)
            }
            .buttonStyle(.plain)
            .frame(width: 28, height: 28)
            .help(showDocsList ? "Hide sidebar" : "Show sidebar")
            .accessibilityLabel(showDocsList ? "Hide document list" : "Show document list")

            Divider().frame(height: 16)

            // AI Assist
            Button {
                showAIAssist.toggle()
            } label: {
                Image(systemName: "sparkles")
                    .font(.system(size: 13))
                    .foregroundStyle(.purple)
                    .frame(width: 26, height: 26)
            }
            .buttonStyle(.plain)
            .help("AI Assist (⌘⇧I)")
            .accessibilityLabel("AI Assist")
            .popover(isPresented: $showAIAssist) {
                AIAssistPopover(
                    inputText: document.content,
                    context: document.title,
                    onAccept: { result in
                        document.content = result
                        showAIAssist = false
                    },
                    onDismiss: {
                        showAIAssist = false
                    }
                )
            }

            Spacer()

            // Document title (editable)
            Text(document.title)
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .frame(maxWidth: 200)

            // Star toggle
            Button {
                document.isStarred.toggle()
            } label: {
                Image(systemName: document.isStarred ? "star.fill" : "star")
                    .font(.system(size: 12))
                    .foregroundStyle(document.isStarred ? .yellow : .secondary)
            }
            .buttonStyle(.plain)
            .help(document.isStarred ? "Unstar" : "Star")
            .accessibilityLabel(document.isStarred ? "Unstar document" : "Star document")

            // Export
            Button {
                showExport = true
            } label: {
                Image(systemName: "arrow.up.doc")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .help("Export (⌘E)")
            .accessibilityLabel("Export document")

            // More options
            Menu {
                Button("Export...") { showExport = true }
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .menuStyle(.borderlessButton)
            .frame(width: 28)
            .accessibilityLabel("More options")
        }
        .padding(.horizontal, 12)
        .frame(height: HubLayout.headerHeight)
        .background(Color.surfaceTertiary.opacity(0.5))
        .sheet(isPresented: $showExport) {
            ExportSheet(
                content: .plainText(document.content, title: document.title),
                onDismiss: { showExport = false }
            )
        }
    }

}
