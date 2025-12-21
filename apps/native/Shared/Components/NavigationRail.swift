//
//  NavigationRail.swift
//  MagnetarStudio
//
//  Navigation rail matching React NavigationRail.tsx specs exactly
//  - 56pt width, gradient background, rounded pill buttons
//  - Top cluster: Chat, Team, Kanban, Database
//  - Bottom cluster: Admin, Settings
//

import SwiftUI

struct NavigationRail: View {
    @Environment(NavigationStore.self) private var navigationStore
    @State private var showSettings = false

    var body: some View {
        VStack(spacing: 0) {
            // Top cluster: workspace buttons
            VStack(spacing: 12) {
                // Chat
                RailButton(
                    icon: "message",
                    workspace: .chat,
                    isActive: navigationStore.activeWorkspace == .chat
                ) {
                    navigationStore.activeWorkspace = .chat
                }
                .help("Chat (⌘1)")

                // Team
                RailButton(
                    icon: "briefcase",
                    workspace: .team,
                    isActive: navigationStore.activeWorkspace == .team
                ) {
                    navigationStore.activeWorkspace = .team
                }
                .help("Team (⌘2)")

                // Kanban
                RailButton(
                    icon: "square.grid.3x2",
                    workspace: .kanban,
                    isActive: navigationStore.activeWorkspace == .kanban
                ) {
                    navigationStore.activeWorkspace = .kanban
                }
                .help("Kanban (⌘3)")

                // Database
                RailButton(
                    icon: "cylinder",
                    workspace: .database,
                    isActive: navigationStore.activeWorkspace == .database
                ) {
                    navigationStore.activeWorkspace = .database
                }
                .help("Database (⌘4)")

                // Insights (Voice Notes)
                RailButton(
                    icon: "waveform",
                    workspace: .insights,
                    isActive: navigationStore.activeWorkspace == .insights
                ) {
                    navigationStore.activeWorkspace = .insights
                }
                .help("Insights (⌘6)")

                // Trust Network
                RailButton(
                    icon: "checkmark.shield",
                    workspace: .trust,
                    isActive: navigationStore.activeWorkspace == .trust
                ) {
                    navigationStore.activeWorkspace = .trust
                }
                .help("Trust Network (⌘7)")
            }
            .padding(.top, 20)

            Spacer()

            // Bottom cluster: Admin + Settings
            VStack(spacing: 12) {
                // Admin
                RailButton(
                    icon: "crown",
                    workspace: .magnetarHub,
                    isActive: navigationStore.activeWorkspace == .magnetarHub
                ) {
                    navigationStore.activeWorkspace = .magnetarHub
                }
                .help("Admin (⌘5)")
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
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
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
