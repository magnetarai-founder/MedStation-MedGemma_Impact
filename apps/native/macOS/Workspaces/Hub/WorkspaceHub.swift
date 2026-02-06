//
//  WorkspaceHub.swift
//  MagnetarStudio
//
//  Main container for the Workspace tab — sidebar + content area.
//  Supports Notes, Docs, Sheets, PDFs, and Voice panels.
//

import SwiftUI

struct WorkspaceHub: View {
    @State private var store = WorkspaceHubStore.shared

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

            // Content area — .id() ensures lazy loading (panel only
            // initializes when first selected, and re-creates on switch)
            activePanelView
                .id(store.selectedPanel)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .transition(.opacity.animation(.easeInOut(duration: 0.15)))
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
        case .team:
            TeamNotesPanel()
        case .automations:
            AutomationListView()
        case .plugins:
            PluginManagerView()
        }
    }
}
