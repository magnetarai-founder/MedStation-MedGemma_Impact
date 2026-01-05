//
//  NavigationRail.swift
//  MagnetarStudio
//
//  Navigation rail matching React NavigationRail.tsx specs exactly
//  - 56pt width, gradient background, rounded pill buttons
//  - Top cluster: Main workspaces (generated from Workspace.topRailWorkspaces)
//  - Bottom cluster: Admin/Hub (generated from Workspace.bottomRailWorkspaces)
//
//  MAINTENANCE: To add a new workspace:
//  1. Add case to Workspace enum in NavigationStore.swift
//  2. Set railIcon and railPosition properties
//  3. Add keyboard shortcut to MagnetarMenuCommands.swift
//

import SwiftUI

struct NavigationRail: View {
    @Environment(NavigationStore.self) private var navigationStore

    var body: some View {
        VStack(spacing: 0) {
            // Top cluster: workspace buttons (generated from Workspace.topRailWorkspaces)
            VStack(spacing: 12) {
                ForEach(Workspace.topRailWorkspaces) { workspace in
                    RailButton(
                        icon: workspace.railIcon,
                        workspace: workspace,
                        isActive: navigationStore.activeWorkspace == workspace
                    ) {
                        navigationStore.activeWorkspace = workspace
                    }
                    .help("\(workspace.displayName) (⌘\(workspace.keyboardShortcut))")
                }
            }
            .padding(.top, 20)

            Spacer()

            // Bottom cluster: admin/hub workspaces (generated from Workspace.bottomRailWorkspaces)
            VStack(spacing: 12) {
                ForEach(Workspace.bottomRailWorkspaces) { workspace in
                    RailButton(
                        icon: workspace.railIcon,
                        workspace: workspace,
                        isActive: navigationStore.activeWorkspace == workspace
                    ) {
                        navigationStore.activeWorkspace = workspace
                    }
                    .help("\(workspace.displayName) (⌘\(workspace.keyboardShortcut))")
                }
            }
            .padding(.bottom, 16)
        }
        .frame(width: 56)
        .background(
            // macOS Tahoe Liquid Glass - refracts content behind, reflects wallpaper
            ZStack {
                // Subtle gradient tint
                LinearGradient(
                    colors: [
                        Color(red: 0.31, green: 0.33, blue: 0.98, opacity: 0.08), // indigo-50/80
                        Color(red: 0.55, green: 0.27, blue: 0.93, opacity: 0.08), // purple-50/80
                        Color(red: 0.24, green: 0.51, blue: 0.98, opacity: 0.08)  // blue-50/80
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
            }
            .navigationGlass()  // Applies @AppStorage("glassOpacity") controlled material
        )
        .overlay(
            // Right border
            Rectangle()
                .fill(Color.white.opacity(0.2))
                .frame(width: 1),
            alignment: .trailing
        )
    }
}

// MARK: - Rail Button Component

struct RailButton: View {
    let icon: String
    let workspace: Workspace
    let isActive: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 22))
                .frame(width: 56, height: 56)
                .foregroundColor(isActive ? .white : (isHovered ? .primary : .secondary))
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(backgroundColor)
                        .shadow(color: isActive ? Color.magnetarPrimary.opacity(0.4) : .clear, radius: 12, x: 0, y: 4)
                )
                .scaleEffect(isHovered && !isActive ? 1.05 : 1.0)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }

    private var backgroundColor: Color {
        if isActive {
            return Color.magnetarPrimary.opacity(0.9)
        } else if isHovered {
            return Color.white.opacity(0.6)
        } else {
            return Color.clear
        }
    }
}

// MARK: - Preview

#Preview {
    NavigationRail()
        .environment(NavigationStore())
        .frame(height: 800)
}
