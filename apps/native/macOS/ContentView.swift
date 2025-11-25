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
