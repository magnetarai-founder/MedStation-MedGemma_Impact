//
//  DatabaseWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Database workspace matching React specs exactly:
//  - Left: 320pt resizable sidebar (FileUpload + icon row + SidebarTabs)
//  - Right: Vertical split (CodeEditor top + ResultsTable bottom)
//

import SwiftUI

struct DatabaseWorkspace: View {
    @State private var sidebarWidth: CGFloat = 320
    @State private var topPaneHeight: CGFloat = 0.33 // 33% default
    @State private var showLibrary = false
    @State private var showQueryHistory = false
    @State private var showJsonConverter = false

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
            Text("Query Library")
                .frame(width: 600, height: 500)
        }
        .sheet(isPresented: $showQueryHistory) {
            Text("Query History")
                .frame(width: 600, height: 500)
        }
        .sheet(isPresented: $showJsonConverter) {
            Text("JSON Converter")
                .frame(width: 600, height: 500)
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

            Spacer()
        }
    }

    // MARK: - Right Content (Vertical Split)

    private func rightContent(geometry: GeometryProxy) -> some View {
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

// MARK: - Icon Toolbar Button

struct IconToolbarButton: View {
    let icon: String
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(isHovered ? Color.magnetarPrimary : .secondary)
                .frame(width: 32, height: 32)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isHovered ? Color.white.opacity(0.6) : Color.clear)
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Drag Handle

struct DragHandle: View {
    @State private var isHovered = false
    @State private var isDragging = false

    var body: some View {
        ZStack {
            // Background bar
            Rectangle()
                .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                .opacity(isDragging ? 1.0 : 0.5)

            // Grip icon (on hover)
            if isHovered || isDragging {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                    )
            }
        }
        .frame(maxWidth: .infinity)
        .contentShape(Rectangle()) // Make entire area draggable
        .onHover { hovering in
            isHovered = hovering
        }
        .gesture(
            DragGesture()
                .onChanged { _ in
                    isDragging = true
                }
                .onEnded { _ in
                    isDragging = false
                }
        )
        .cursor(.resizeUpDown)
    }
}

// MARK: - Cursor Extension

extension View {
    func cursor(_ cursor: NSCursor) -> some View {
        self.onContinuousHover { phase in
            switch phase {
            case .active:
                cursor.push()
            case .ended:
                NSCursor.pop()
            }
        }
    }
}

// MARK: - Preview

#Preview {
    DatabaseWorkspace()
        .frame(width: 1200, height: 800)
}
