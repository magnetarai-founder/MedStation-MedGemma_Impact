//
//  ContentView.swift
//  MagnetarStudio (macOS)
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI
import LocalAuthentication
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ContentView")

struct ContentView: View {
    @Environment(AuthStore.self) private var authStore
    @Environment(DatabaseStore.self) private var databaseStore
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
        .environment(authStore)
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
            logger.info("Biometric auto-login failed: \(error.localizedDescription)")
            return
        }
    }
}

// MARK: - Main App View (Active Workspaces)

struct MainAppView: View {
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(ChatStore.self) private var chatStore
    @Environment(VaultPermissionManager.self) private var permissionManager
    @Environment(AuthStore.self) private var authStore
    @State private var workspaceError: WorkspaceError?
    @State private var aiPanelStore = UniversalAIPanelStore.shared
    @AppStorage("autoLockEnabled") private var autoLockEnabled = true
    @AppStorage("autoLockTimeout") private var autoLockTimeout = 15

    var body: some View {
        ZStack {
            // Main content - Phase 2B: Simplified layout without NavigationRail
            VStack(spacing: 0) {
                // Top: Header bar with integrated tab switcher
                Header()

                // Body: Workspace + optional AI side panel
                HStack(spacing: 0) {
                    Group {
                        if let error = workspaceError {
                            WorkspaceErrorView(
                                error: error,
                                workspace: navigationStore.activeWorkspace,
                                onRetry: { workspaceError = nil }
                            )
                        } else {
                            activeWorkspaceView
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .transition(.magnetarFade)

                    // Universal AI Panel (toggled via Header sparkles or ⇧⌘P)
                    if aiPanelStore.isVisible {
                        ResizableDivider(
                            dimension: $aiPanelStore.panelWidth,
                            axis: .horizontal,
                            minValue: Double(UniversalAIPanelStore.minWidth),
                            maxValue: Double(UniversalAIPanelStore.maxWidth),
                            defaultValue: 320,
                            invertDrag: true
                        )

                        UniversalAIPanel()
                            .frame(width: CGFloat(aiPanelStore.panelWidth))
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .onChange(of: navigationStore.activeWorkspace) { _, _ in
                // Clear error when switching workspaces
                workspaceError = nil
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
        .task(id: autoLockEnabled) {
            guard autoLockEnabled, autoLockTimeout > 0 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(30))
                guard autoLockEnabled else { break }
                // Check system-wide idle time via Quartz Event Services
                let mouseIdle = CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: .mouseMoved)
                let keyIdle = CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: .keyDown)
                let idleSeconds = min(mouseIdle, keyIdle)
                let timeoutSeconds = Double(autoLockTimeout) * 60
                if idleSeconds > timeoutSeconds {
                    logger.info("Auto-lock triggered after \(Int(idleSeconds))s system idle")
                    authStore.lock()
                    break
                }
            }
        }
    }

    // MARK: - Active Workspace View

    @ViewBuilder
    private var activeWorkspaceView: some View {
        switch navigationStore.activeWorkspace {
        // Core workspaces (4 main tabs: Hub, Files, Code, Chat)
        case .chat:
            ChatWorkspace()
        case .files:
            VaultWorkspace()
        case .workspace:
            WorkspaceHub()
        case .code:
            CodeWorkspace()

        // Spawnable workspaces (open as separate windows)
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

        // Team — gated by FeatureFlags; falls back to workspace hub
        case .team:
            if FeatureFlags.shared.team {
                TeamWorkspace()
            } else {
                WorkspaceHub()
            }
        }
    }
}

// MARK: - Workspace Error Types

enum WorkspaceError: Error, LocalizedError {
    case loadFailed(String)
    case networkError(String)
    case authenticationRequired
    case unknown(Error)

    var errorDescription: String? {
        switch self {
        case .loadFailed(let message):
            return "Failed to load workspace: \(message)"
        case .networkError(let message):
            return "Network error: \(message)"
        case .authenticationRequired:
            return "Authentication required"
        case .unknown(let error):
            return "An error occurred: \(error.localizedDescription)"
        }
    }

    var recoverySuggestion: String {
        switch self {
        case .loadFailed:
            return "Try refreshing or check your connection."
        case .networkError:
            return "Check your network connection and try again."
        case .authenticationRequired:
            return "Please log in to continue."
        case .unknown:
            return "Try again or restart the app if the problem persists."
        }
    }
}

// MARK: - Workspace Error View

struct WorkspaceErrorView: View {
    let error: WorkspaceError
    let workspace: Workspace
    let onRetry: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("Something went wrong")
                .font(.title2.bold())

            Text(error.localizedDescription)
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Text(error.recoverySuggestion)
                .font(.caption)
                .foregroundColor(.secondary)

            HStack(spacing: 16) {
                Button("Try Again") {
                    onRetry()
                }
                .buttonStyle(.borderedProminent)

                Button("Report Issue") {
                    if let url = URL(string: "https://github.com/MagnetarStudio/MagnetarStudio/issues") {
                        NSWorkspace.shared.open(url)
                    }
                }
                .buttonStyle(.bordered)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - Preview

#Preview("Welcome") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
        .environment(DatabaseStore.shared)
}

#Preview("Authenticated") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
        .environment(DatabaseStore.shared)
}
