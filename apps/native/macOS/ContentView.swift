//
//  ContentView.swift
//  MagnetarStudio (macOS)
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI
import LocalAuthentication

struct ContentView: View {
    @StateObject private var authStore = AuthStore.shared
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var attemptedBiometricLogin = false

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
            }
        }
        .task {
            // Bootstrap: validate existing token on launch
            await authStore.bootstrap()

            // If authenticated, create database session
            if authStore.authState == .authenticated {
                await databaseStore.createSession()
            }

            // Attempt biometric login on app launch if not already authenticated and has saved credentials
            if authStore.authState == .welcome && !attemptedBiometricLogin {
                attemptedBiometricLogin = true
                await attemptBiometricAutoLogin()
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

    // MARK: - Biometric Auto-Login

    private func attemptBiometricAutoLogin() async {
        let keychainService = KeychainService.shared
        let biometricService = BiometricAuthService.shared

        // Check if biometric credentials are saved
        guard keychainService.hasBiometricCredentials(),
              biometricService.isBiometricAvailable else {
            return
        }

        do {
            // Authenticate with biometrics (silently fail if user cancels)
            let success = try await biometricService.authenticate(
                reason: "Sign in to MagnetarStudio"
            )

            guard success else {
                return
            }

            // Load credentials from keychain
            let context = LAContext()
            let credentials = try keychainService.loadBiometricCredentials(context: context)

            // Login with stored credentials
            let response = try await AuthService.shared.login(
                username: credentials.username,
                password: credentials.password
            )

            // Save token and trigger bootstrap
            await authStore.saveToken(response.token)

        } catch BiometricError.userCancel {
            // User cancelled - silently ignore
            return
        } catch {
            // Other errors - silently ignore (user can manually login)
            print("Biometric auto-login failed: \(error.localizedDescription)")
            return
        }
    }
}

// MARK: - Main App View (Active Workspaces)

struct MainAppView: View {
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(ChatStore.self) private var chatStore
    @StateObject private var permissionManager = VaultPermissionManager.shared

    var body: some View {
        ZStack {
            // Main content
            VStack(spacing: 0) {
                // Top: Header bar
                Header()

                // Body: HStack with Navigation Rail + Tab Content
                HStack(spacing: 0) {
                    // Left: Navigation Rail (56pt wide)
                    NavigationRail()

                    Divider()

                    // Right: Tab content (lazy loading for performance)
                    Group {
                        switch navigationStore.activeWorkspace {
                        case .chat:
                            ChatWorkspace()
                        case .team:
                            TeamWorkspace()
                        case .code:
                            CodeWorkspace()
                        case .kanban:
                            KanbanWorkspace()
                        case .database:
                            DatabaseWorkspace()
                        case .insights:
                            InsightsWorkspace()
                        case .trust:
                            TrustWorkspace()
                        case .magnetarHub:
                            MagnetarHubWorkspace()
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .transition(.magnetarFade)
                }
            }

            // CRITICAL: File permission modal overlay (Phase 3)
            // This is BLOCKING - models cannot access file contents without permission
            if permissionManager.showPermissionModal,
               let request = permissionManager.pendingRequest {
                Color.black.opacity(0.5)
                    .ignoresSafeArea()
                    .transition(.opacity)

                FileAccessPermissionModal(
                    request: request,
                    onGrant: { scope in
                        await permissionManager.grantPermission(scope: scope)
                    },
                    onDeny: {
                        permissionManager.denyPermission()
                    },
                    onCancel: {
                        permissionManager.cancelPermission()
                    }
                )
                .transition(.scale.combined(with: .opacity))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .animation(.easeInOut(duration: 0.2), value: permissionManager.showPermissionModal)
        .withNetworkFirewall() // Enable network firewall with approval modals
    }
}

// MARK: - Preview

#Preview("Welcome") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
        .environmentObject(DatabaseStore.shared)
}

#Preview("Authenticated") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
        .environmentObject(DatabaseStore.shared)
}
