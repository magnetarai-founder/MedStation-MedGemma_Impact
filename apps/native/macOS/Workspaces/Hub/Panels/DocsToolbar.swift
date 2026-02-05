//
//  DocsToolbar.swift
//  MagnetarStudio
//
//  Rich text formatting toolbar for the Docs panel.
//  Provides formatting controls above the document editor.
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

            Divider().frame(height: 16)

            // Text formatting group
            Group {
                toolbarButton(icon: "bold", help: "Bold (⌘B)")
                toolbarButton(icon: "italic", help: "Italic (⌘I)")
                toolbarButton(icon: "underline", help: "Underline (⌘U)")
                toolbarButton(icon: "strikethrough", help: "Strikethrough")
            }

            Divider().frame(height: 16)

            // Alignment group
            Group {
                toolbarButton(icon: "text.alignleft", help: "Align Left")
                toolbarButton(icon: "text.aligncenter", help: "Center")
                toolbarButton(icon: "text.alignright", help: "Align Right")
            }

            Divider().frame(height: 16)

            // Insert group
            Group {
                toolbarButton(icon: "list.bullet", help: "Bullet List")
                toolbarButton(icon: "list.number", help: "Numbered List")
                toolbarButton(icon: "checklist", help: "Checklist")
                toolbarButton(icon: "tablecells", help: "Insert Table")
            }

            Divider().frame(height: 16)

            // Media
            toolbarButton(icon: "photo", help: "Insert Image")
            toolbarButton(icon: "link", help: "Insert Link")

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

            // More options
            Menu {
                Button("Export...") { showExport = true }
                Divider()
                Button("Document Info...") {}
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .menuStyle(.borderlessButton)
            .frame(width: 28)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.surfaceTertiary.opacity(0.5))
        .sheet(isPresented: $showExport) {
            ExportSheet(
                content: .plainText(document.content, title: document.title),
                onDismiss: { showExport = false }
            )
        }
    }

    private func toolbarButton(icon: String, help: String) -> some View {
        Button {} label: {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .frame(width: 26, height: 26)
        }
        .buttonStyle(.plain)
        .help(help)
    }
}
