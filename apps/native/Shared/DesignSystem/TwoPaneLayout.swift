//
//  TwoPaneLayout.swift
//  MagnetarStudio
//
//  Two-pane layout matching the React app structure:
//  Horizontal toolbar + Left sidebar + Main content
//

import SwiftUI

/// Two-pane layout with toolbar (matching React app structure)
struct TwoPaneLayout<Toolbar: View, LeftPane: View, RightPane: View>: View {
    let toolbar: Toolbar
    let leftPane: LeftPane
    let rightPane: RightPane

    init(
        @ViewBuilder toolbar: () -> Toolbar,
        @ViewBuilder leftPane: () -> LeftPane,
        @ViewBuilder rightPane: () -> RightPane
    ) {
        self.toolbar = toolbar()
        self.leftPane = leftPane()
        self.rightPane = rightPane()
    }

    var body: some View {
        VStack(spacing: 0) {
            // Horizontal Toolbar
            toolbar
                .frame(height: 52)
                .padding(.horizontal, 16)
                .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Two panes below
            HStack(spacing: 0) {
                // Left Pane: Sidebar (250-300px)
                leftPane
                    .frame(minWidth: 220, idealWidth: 260, maxWidth: 320)
                    .background(Color.surfaceSecondary.opacity(0.5))

                Divider()

                // Right Pane: Main Content (flexible)
                rightPane
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}

/// Workspace Toolbar - horizontal quick access bar
struct WorkspaceToolbar<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        HStack(spacing: 12) {
            content
            Spacer()
        }
    }
}

/// Toolbar Button - consistent styling
struct ToolbarButton: View {
    let title: String
    let icon: String
    let style: ButtonStyle
    let action: () -> Void

    enum ButtonStyle {
        case primary
        case secondary
        case icon
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                if style != .icon {
                    Text(title)
                        .font(.system(size: 13, weight: .medium))
                }
            }
            .padding(.horizontal, style == .icon ? 8 : 12)
            .padding(.vertical, 6)
            .background(backgroundColor)
            .foregroundColor(foregroundColor)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
    }

    private var backgroundColor: Color {
        switch style {
        case .primary:
            return Color.magnetarPrimary
        case .secondary:
            return Color.surfaceSecondary
        case .icon:
            return Color.clear
        }
    }

    private var foregroundColor: Color {
        switch style {
        case .primary:
            return .white
        case .secondary, .icon:
            return .textPrimary
        }
    }
}

/// Toolbar Divider - vertical separator
struct ToolbarDivider: View {
    var body: some View {
        Rectangle()
            .fill(Color.gray.opacity(0.3))
            .frame(width: 1, height: 24)
    }
}

// MARK: - Preview

#Preview("Two Pane Layout") {
    TwoPaneLayout {
        // Toolbar
        WorkspaceToolbar {
            ToolbarButton(title: "New Chat", icon: "plus", style: .primary, action: {})
            ToolbarButton(title: "Select", icon: "checkmark.square", style: .secondary, action: {})
            ToolbarDivider()
            ToolbarButton(title: "", icon: "magnifyingglass", style: .icon, action: {})
            ToolbarButton(title: "", icon: "slider.horizontal.3", style: .icon, action: {})
        }
    } leftPane: {
        // Left Sidebar
        VStack(spacing: 0) {
            List {
                Label("Inbox", systemImage: "tray")
                Label("Sent", systemImage: "paperplane")
                Label("Drafts", systemImage: "doc.text")
            }
            .listStyle(.sidebar)
        }
    } rightPane: {
        // Main Content
        VStack {
            Text("Main Content Area")
                .font(.title)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    .frame(width: 1200, height: 800)
}
