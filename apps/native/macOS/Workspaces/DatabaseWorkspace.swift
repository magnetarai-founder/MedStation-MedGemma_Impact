//
//  DatabaseWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Database workspace matching React specs exactly:
//  - Left: 320pt resizable sidebar (FileUpload + icon row + SidebarTabs)
//  - Right: Vertical split (CodeEditor top + ResultsTable bottom)
//

import SwiftUI

// MARK: - Database View Tab
enum DatabaseViewTab: String, CaseIterable {
    case dataLab = "Data Lab"
    case sqlEditor = "SQL Editor"

    var icon: String {
        switch self {
        case .dataLab: return "sparkles"
        case .sqlEditor: return "terminal"
        }
    }
}

struct DatabaseWorkspace: View {
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var sidebarWidth: CGFloat = 320
    @State private var topPaneHeight: CGFloat = 0.33 // 33% default
    @State private var showLibrary = false
    @State private var showQueryHistory = false
    @State private var showJsonConverter = false
    @State private var activeTab: DatabaseViewTab = .dataLab

    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 0) {
                // Left Sidebar (resizable, 320pt default)
                leftSidebar
                    .frame(width: max(320, min(sidebarWidth, geometry.size.width * 0.4)))

                Divider()

                // Right Content (vertical split)
                rightContent(geometry: geometry)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .sheet(isPresented: $showLibrary) {
            QueryLibraryModal(isPresented: $showLibrary, databaseStore: databaseStore)
        }
        .sheet(isPresented: $showQueryHistory) {
            QueryHistoryModal(isPresented: $showQueryHistory, databaseStore: databaseStore)
        }
        .sheet(isPresented: $showJsonConverter) {
            JsonConverterModal(isPresented: $showJsonConverter, databaseStore: databaseStore)
        }
    }

    // MARK: - Left Sidebar

    private var leftSidebar: some View {
        VStack(spacing: 0) {
            // Top: File Upload
            FileUpload()

            // Icon toolbar row
            iconToolbarRow
                .padding(.vertical, 8)
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Tabs: Columns | Logs
            SidebarTabs()
        }
        .background(Color(.controlBackgroundColor).opacity(0.3))
    }

    private var iconToolbarRow: some View {
        HStack(spacing: 8) {
            Spacer()

            // Query Library
            IconToolbarButton(icon: "folder", action: {
                showLibrary = true
            })
            .help("Query Library")

            // Query History
            IconToolbarButton(icon: "clock", action: {
                showQueryHistory = true
            })
            .help("Query History")

            // JSON Converter
            IconToolbarButton(icon: "doc.text", action: {
                showJsonConverter = true
            })
            .help("JSON Converter")

            // Clear workspace
            IconToolbarButton(icon: "trash", action: {
                NotificationCenter.default.post(name: .clearWorkspace, object: nil)
            })
            .help("Clear Workspace")

            Spacer()
        }
    }

    // MARK: - Right Content (Tab Toolbar + Content)

    private func rightContent(geometry: GeometryProxy) -> some View {
        VStack(spacing: 0) {
            // Tab toolbar
            tabToolbar

            Divider()

            // Tab content
            Group {
                switch activeTab {
                case .dataLab:
                    CombinedDataLabView()
                case .sqlEditor:
                    sqlEditorView(geometry: geometry)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Tab Toolbar

    private var tabToolbar: some View {
        HStack(spacing: 0) {
            ForEach(DatabaseViewTab.allCases, id: \.self) { tab in
                Button(action: {
                    withAnimation(.magnetarStandard) {
                        activeTab = tab
                    }
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: tab.icon)
                            .font(.system(size: 14))
                        Text(tab.rawValue)
                            .font(.system(size: 13, weight: .medium))
                    }
                    .foregroundColor(activeTab == tab ? .magnetarPrimary : .secondary)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        Rectangle()
                            .fill(activeTab == tab ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
                    )
                    .overlay(
                        Rectangle()
                            .fill(activeTab == tab ? Color.magnetarPrimary : Color.clear)
                            .frame(height: 2),
                        alignment: .bottom
                    )
                }
                .buttonStyle(.plain)
            }

            Spacer()
        }
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - SQL Editor View (original content)

    private func sqlEditorView(geometry: GeometryProxy) -> some View {
        let totalHeight = geometry.size.height
        let topHeight = totalHeight * topPaneHeight

        return VStack(spacing: 0) {
            // Top: Code Editor
            CodeEditor()
                .frame(height: max(150, topHeight))

            // Drag handle
            DragHandle()
                .frame(height: 6)
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            let newHeight = topHeight + value.translation.height
                            let ratio = newHeight / totalHeight
                            topPaneHeight = max(0.2, min(0.8, ratio))
                        }
                )

            // Bottom: Results Table
            ResultsTable()
                .frame(maxHeight: .infinity)
        }
    }
}



// MARK: - Preview

#Preview {
    DatabaseWorkspace()
        .frame(width: 1200, height: 800)
}

