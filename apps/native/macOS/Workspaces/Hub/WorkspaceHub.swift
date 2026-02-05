//
//  WorkspaceHub.swift
//  MagnetarStudio
//
//  Main container for the Workspace tab — sidebar + content area.
//  Supports Notes, Docs, Sheets, PDFs, and Voice panels.
//

import SwiftUI

struct WorkspaceHub: View {
    @State private var store = WorkspaceHubStore()

    var body: some View {
        HStack(spacing: 0) {
            // Sidebar
            WorkspaceSidebarView(store: store)
                .frame(width: store.sidebarWidth)

            // Resizable divider
            ResizableDivider(
                dimension: $store.sidebarWidth,
                axis: .horizontal,
                minValue: 160,
                maxValue: 350,
                defaultValue: 220
            )

            // Content area
            activePanelView
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Active Panel

    @ViewBuilder
    private var activePanelView: some View {
        switch store.selectedPanel {
        case .notes:
            NotesPanel()
        case .docs:
            DocsPanel()
        case .sheets:
            SheetsPanel()
        case .pdf:
            PDFPanel()
        case .voice:
            VoicePanel()
        }
    }
}

// MARK: - Panel Placeholder (replaced in Phases 2-5)

struct WorkspacePanelPlaceholder: View {
    let panel: WorkspacePanelType

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: panel.icon)
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)

            Text(panel.displayName)
                .font(.title2.bold())
                .foregroundStyle(.primary)

            Text("Coming soon — \(panel.displayName) panel")
                .font(.body)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }
}
