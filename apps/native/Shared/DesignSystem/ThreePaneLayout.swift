//
//  ThreePaneLayout.swift
//  MagnetarStudio
//
//  Uniform three-pane Outlook-style layout used across all workspaces.
//  Inspired by macOS Tahoe's Liquid Glass design.
//

import SwiftUI

/// Uniform three-pane layout following Outlook for Mac design patterns
struct ThreePaneLayout<LeftPane: View, MiddlePane: View, RightPane: View>: View {
    let leftPane: LeftPane
    let middlePane: MiddlePane
    let rightPane: RightPane

    init(
        @ViewBuilder leftPane: () -> LeftPane,
        @ViewBuilder middlePane: () -> MiddlePane,
        @ViewBuilder rightPane: () -> RightPane
    ) {
        self.leftPane = leftPane()
        self.middlePane = middlePane()
        self.rightPane = rightPane()
    }

    var body: some View {
        HStack(spacing: 0) {
            // Left Pane: Navigation/Folder List (~220-280px)
            leftPane
                .frame(minWidth: 200, idealWidth: 240, maxWidth: 300)
                .background(Color.surfaceSecondary.opacity(0.5))

            Divider()

            // Middle Pane: Item List (~300-400px)
            middlePane
                .frame(minWidth: 280, idealWidth: 350, maxWidth: 450)
                .background(Color.surfaceSecondary.opacity(0.3))

            Divider()

            // Right Pane: Detail/Reading View (flexible)
            rightPane
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

/// Pane header with consistent styling across all workspaces
struct PaneHeader: View {
    let title: String
    let icon: String?
    let subtitle: String?
    let action: (() -> Void)?
    let actionIcon: String?

    init(
        title: String,
        icon: String? = nil,
        subtitle: String? = nil,
        action: (() -> Void)? = nil,
        actionIcon: String? = nil
    ) {
        self.title = title
        self.icon = icon
        self.subtitle = subtitle
        self.action = action
        self.actionIcon = actionIcon
    }

    var body: some View {
        HStack(spacing: 12) {
            // Icon (optional)
            if let icon = icon {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundColor(.secondary)
            }

            // Title and subtitle
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                    .foregroundColor(.textPrimary)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            // Action button (optional)
            if let action = action, let actionIcon = actionIcon {
                Button(action: action) {
                    Image(systemName: actionIcon)
                        .font(.title3)
                        .foregroundStyle(LinearGradient.magnetarGradient)
                }
                .buttonStyle(.plain)
            }
        }
        .frame(height: 44)
        .padding(.horizontal, 16)
        .background(Color.surfaceTertiary.opacity(0.3))
    }
}

/// Empty state view for panes with no content
struct PaneEmptyState: View {
    let icon: String
    let title: String
    let subtitle: String?
    let actionTitle: String?
    let action: (() -> Void)?

    init(
        icon: String,
        title: String,
        subtitle: String? = nil,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.title = title
        self.subtitle = subtitle
        self.actionTitle = actionTitle
        self.action = action
    }

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: icon)
                .font(.system(size: 56))
                .foregroundStyle(LinearGradient.magnetarGradient.opacity(0.7))

            VStack(spacing: 8) {
                Text(title)
                    .font(.title3)
                    .fontWeight(.semibold)
                    .foregroundColor(.textPrimary)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
            }

            if let actionTitle = actionTitle, let action = action {
                GlassButton(actionTitle, icon: "plus", style: .primary, action: action)
                    .frame(width: 180)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

// MARK: - Preview

#Preview("Three Pane Layout") {
    ThreePaneLayout {
        // Left Pane
        VStack(spacing: 0) {
            PaneHeader(
                title: "Folders",
                icon: "folder",
                action: {},
                actionIcon: "plus.circle.fill"
            )

            Divider()

            List {
                Label("Inbox", systemImage: "tray")
                Label("Sent", systemImage: "paperplane")
                Label("Drafts", systemImage: "doc.text")
                Label("Archive", systemImage: "archivebox")
            }
            .listStyle(.sidebar)
        }
    } middlePane: {
        // Middle Pane
        VStack(spacing: 0) {
            PaneHeader(
                title: "Messages",
                subtitle: "24 unread"
            )

            Divider()

            List(0..<10) { i in
                VStack(alignment: .leading, spacing: 4) {
                    Text("Message \(i)")
                        .font(.headline)
                    Text("Preview text...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .listStyle(.plain)
        }
    } rightPane: {
        // Right Pane
        PaneEmptyState(
            icon: "envelope.open",
            title: "No message selected",
            subtitle: "Select a message to read"
        )
    }
    .frame(width: 1200, height: 800)
}
