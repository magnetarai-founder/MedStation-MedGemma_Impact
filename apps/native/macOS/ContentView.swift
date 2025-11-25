//
//  ContentView.swift
//  MagnetarStudio (macOS)
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var authStore = AuthStore.shared
    @StateObject private var databaseStore = DatabaseStore.shared
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()

    var body: some View {
        Group {
            switch authStore.authState {
            case .welcome:
                // Show login/welcome screen
                WelcomeView()

            case .checking:
                // Show loading while validating token
                LoadingView(message: "Checking authentication...")

            case .setupNeeded:
                // Show setup wizard
                SetupWizardView()

            case .authenticated:
                // Main app with navigation
                MainAppView()
                    .environment(navigationStore)
                    .environment(chatStore)
                    .environmentObject(databaseStore)
            }
        }
        .task {
            // Bootstrap: validate existing token on launch
            await authStore.bootstrap()

            // If authenticated, create database session
            if authStore.authState == .authenticated {
                await databaseStore.createSession()
            }
        }
        .onChange(of: authStore.authState) { _, newState in
            // Create session when user becomes authenticated
            if newState == .authenticated {
                Task {
                    await databaseStore.createSession()
                }
            }
        }
        .environmentObject(authStore)
    }
}

// MARK: - Main App View (Active Workspaces)

struct MainAppView: View {
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(ChatStore.self) private var chatStore

    var body: some View {
        VStack(spacing: 0) {
            // Top: Header bar
            Header()

            // Body: HStack with Navigation Rail + Tab Content
            HStack(spacing: 0) {
                // Left: Navigation Rail (56pt wide)
                NavigationRail()

                Divider()

                // Right: Tab content (ZStack for tab switching)
                ZStack {
                    // Each workspace fills the entire space, only one visible at a time

                    // Chat tab
                    ChatWorkspace()
                        .opacity(navigationStore.activeWorkspace == .chat ? 1 : 0)
                        .zIndex(navigationStore.activeWorkspace == .chat ? 1 : 0)

                    // Team tab
                    TeamWorkspace()
                        .opacity(navigationStore.activeWorkspace == .team ? 1 : 0)
                        .zIndex(navigationStore.activeWorkspace == .team ? 1 : 0)

                    // Kanban tab
                    KanbanWorkspace()
                        .opacity(navigationStore.activeWorkspace == .kanban ? 1 : 0)
                        .zIndex(navigationStore.activeWorkspace == .kanban ? 1 : 0)

                    // Database tab (default)
                    DatabaseWorkspace()
                        .opacity(navigationStore.activeWorkspace == .database ? 1 : 0)
                        .zIndex(navigationStore.activeWorkspace == .database ? 1 : 0)

                    // Admin/MagnetarHub tab
                    MagnetarHubWorkspace()
                        .opacity(navigationStore.activeWorkspace == .magnetarHub ? 1 : 0)
                        .zIndex(navigationStore.activeWorkspace == .magnetarHub ? 1 : 0)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Preview

#Preview("Welcome") {
    ContentView()
        .frame(width: 1200, height: 800)
}

#Preview("Authenticated") {
    ContentView()
        .frame(width: 1200, height: 800)
}
