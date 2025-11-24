//
//  ContentView.swift
//  MagnetarStudio (macOS)
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI

struct ContentView: View {
    @Environment(UserStore.self) private var userStore
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()

    var body: some View {
        Group {
            if userStore.isAuthenticated {
                // Main app with navigation
                MainAppView()
                    .environment(navigationStore)
                    .environment(chatStore)
            } else {
                // Login/Register screen
                AuthenticationView()
            }
        }
        .task {
            // Check for existing session on launch
            await userStore.checkSession()
        }
    }
}

// MARK: - Authentication View

struct AuthenticationView: View {
    @Environment(UserStore.self) private var userStore

    @State private var username: String = ""
    @State private var password: String = ""
    @State private var isRegistering: Bool = false
    @State private var email: String = ""

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient.magnetarGradient
                .ignoresSafeArea()

            // Login/Register card
            LiquidGlassPanel(material: .thick) {
                VStack(spacing: 24) {
                    // Logo and title
                    VStack(spacing: 8) {
                        Image(systemName: "sparkles")
                            .font(.system(size: 48))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("MagnetarStudio")
                            .font(.largeTitle)
                            .fontWeight(.bold)

                        Text("Professional AI Platform")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.bottom, 16)

                    // Input fields
                    VStack(spacing: 16) {
                        TextField("Username", text: $username)
                            .textFieldStyle(.roundedBorder)
                            .frame(height: 40)

                        if isRegistering {
                            TextField("Email (optional)", text: $email)
                                .textFieldStyle(.roundedBorder)
                                .frame(height: 40)
                        }

                        SecureField("Password", text: $password)
                            .textFieldStyle(.roundedBorder)
                            .frame(height: 40)
                    }

                    // Error message
                    if let error = userStore.error {
                        Text(error.localizedDescription)
                            .font(.caption)
                            .foregroundColor(.error)
                            .padding(.horizontal)
                    }

                    // Action buttons
                    VStack(spacing: 12) {
                        GlassButton(
                            isRegistering ? "Create Account" : "Sign In",
                            icon: isRegistering ? "person.badge.plus" : "person.fill",
                            style: .primary
                        ) {
                            Task {
                                do {
                                    if isRegistering {
                                        try await userStore.register(
                                            username: username,
                                            password: password,
                                            email: email.isEmpty ? nil : email
                                        )
                                    } else {
                                        try await userStore.login(
                                            username: username,
                                            password: password
                                        )
                                    }
                                } catch {
                                    // Error already set in userStore
                                    print("Authentication failed: \(error)")
                                }
                            }
                        }
                        .disabled(username.isEmpty || password.isEmpty || userStore.isLoading)

                        Button {
                            isRegistering.toggle()
                            email = ""
                            userStore.error = nil
                        } label: {
                            Text(isRegistering ? "Already have an account? Sign in" : "Don't have an account? Register")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .buttonStyle(.plain)
                    }

                    // Biometric info
                    if KeychainManager.shared.biometricsAvailable() {
                        HStack(spacing: 8) {
                            Image(systemName: biometricIcon)
                                .font(.caption)
                            Text("Your credentials will be protected with \(KeychainManager.shared.biometricType().displayName)")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 8)
                    }
                }
                .padding(32)
            }
            .frame(width: 450)

            // Loading overlay
            if userStore.isLoading {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()

                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)
            }
        }
    }

    private var biometricIcon: String {
        switch KeychainManager.shared.biometricType() {
        case .faceID: return "faceid"
        case .touchID: return "touchid"
        case .opticID: return "opticid"
        case .none: return "lock.fill"
        }
    }
}

// MARK: - Main App View

struct MainAppView: View {
    @Environment(UserStore.self) private var userStore
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(ChatStore.self) private var chatStore

    var body: some View {
        @Bindable var navStore = navigationStore

        NavigationSplitView {
            // Sidebar with workspace tabs
            List(Workspace.allCases, selection: $navStore.activeWorkspace) { workspace in
                NavigationLink(value: workspace) {
                    Label(workspace.displayName, systemImage: workspace.icon)
                }
                .keyboardShortcut(
                    KeyEquivalent(Character(workspace.keyboardShortcut)),
                    modifiers: .command
                )
            }
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 250)
            .toolbar {
                ToolbarItem {
                    Button {
                        navigationStore.toggleSidebar()
                    } label: {
                        Image(systemName: "sidebar.left")
                    }
                }
            }
        } detail: {
            // Main workspace content
            Group {
                switch navigationStore.activeWorkspace {
                case .team:
                    TeamWorkspace()
                case .chat:
                    ChatWorkspace()
                case .database:
                    DatabaseWorkspace()
                case .kanban:
                    KanbanWorkspace()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

// MARK: - Preview

#Preview("Authenticated") {
    ContentView()
        .environment({
            let store = UserStore()
            store.isAuthenticated = true
            store.user = User(
                id: UUID(),
                username: "testuser",
                role: "member"
            )
            return store
        }())
        .frame(width: 1200, height: 800)
}

#Preview("Login") {
    ContentView()
        .environment(UserStore())
        .frame(width: 1200, height: 800)
}
