//
//  ContentView.swift
//  MedStation
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI
import LocalAuthentication
import AppKit
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ContentView")

struct ContentView: View {
    @Environment(AuthStore.self) private var authStore
    @State private var attemptedBiometricLogin = false

    var body: some View {
        Group {
            switch authStore.authState {
            case .welcome:
                WelcomeView()

            case .checking:
                LoadingView(message: "Checking authentication...")

            case .setupNeeded:
                SetupWizardView()

            case .authenticated:
                MainAppView()
            }
        }
        .task {
            await authStore.bootstrap()

            if authStore.authState == .welcome && !attemptedBiometricLogin {
                attemptedBiometricLogin = true
                await attemptBiometricAutoLogin()
            }
        }
        .environment(authStore)
    }

    // MARK: - Biometric Auto-Login

    private func attemptBiometricAutoLogin() async {
        let keychainService = KeychainService.shared
        let biometricService = BiometricAuthService.shared

        guard keychainService.hasBiometricCredentials(),
              biometricService.isBiometricAvailable else {
            return
        }

        do {
            let success = try await biometricService.authenticate(
                reason: "Sign in to MedStation"
            )

            guard success else { return }

            let context = LAContext()
            let credentials = try keychainService.loadBiometricCredentials(context: context)

            let response = try await AuthService.shared.login(
                username: credentials.username,
                password: credentials.password
            )

            await authStore.saveToken(response.token)

        } catch BiometricError.userCancel {
            return
        } catch {
            logger.info("Biometric auto-login failed: \(error.localizedDescription)")
            return
        }
    }
}

// MARK: - Main App View

struct MainAppView: View {
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(AuthStore.self) private var authStore
    @AppStorage("autoLockEnabled") private var autoLockEnabled = true
    @AppStorage("autoLockTimeout") private var autoLockTimeout = 15

    var body: some View {
        VStack(spacing: 0) {
            // Main content: Medical workspace
            WorkspaceHub()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .task(id: autoLockEnabled) {
            guard autoLockEnabled, autoLockTimeout > 0 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(30))
                guard autoLockEnabled else { break }
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

// MARK: - Preview

#Preview("Welcome") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
}

#Preview("Authenticated") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
}
