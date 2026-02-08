//
//  WelcomeView.swift
//  MagnetarStudio
//
//  Login/Register screen shown when authState == .welcome
//

import SwiftUI
import LocalAuthentication
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "WelcomeView")

struct WelcomeView: View {
    @Environment(AuthStore.self) private var authStore

    @State private var username: String = ""
    @State private var password: String = ""
    @State private var email: String = ""
    @State private var isRegistering: Bool = false
    @State private var enableBiometric: Bool = false

    private let biometricService = BiometricAuthService.shared
    private let keychainService = KeychainService.shared

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
                            .foregroundStyle(.secondary)
                    }
                    .padding(.bottom, 16)

                    // Input fields
                    VStack(spacing: 16) {
                        TextField("Username", text: $username)
                            .textFieldStyle(.roundedBorder)
                            .frame(height: 40)
                            .onSubmit {
                                Task {
                                    await handleAuth()
                                }
                            }

                        if isRegistering {
                            TextField("Email (optional)", text: $email)
                                .textFieldStyle(.roundedBorder)
                                .frame(height: 40)
                                .onSubmit {
                                    Task {
                                        await handleAuth()
                                    }
                                }
                        }

                        SecureField("Password", text: $password)
                            .textFieldStyle(.roundedBorder)
                            .frame(height: 40)
                            .onSubmit {
                                Task {
                                    await handleAuth()
                                }
                            }
                    }

                    // Error message
                    if let error = authStore.error {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
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
                                await handleAuth()
                            }
                        }
                        .disabled(username.isEmpty || password.isEmpty || authStore.loading)

                        // Biometric toggle (only show when logging in, not registering)
                        if !isRegistering && biometricService.isBiometricAvailable {
                            Toggle(isOn: $enableBiometric) {
                                HStack(spacing: 6) {
                                    Image(systemName: biometricService.biometricType().icon)
                                        .font(.caption)
                                    Text("Enable \(biometricService.biometricType().displayName)")
                                        .font(.caption)
                                }
                                .foregroundStyle(.secondary)
                            }
                            .toggleStyle(.checkbox)
                        }

                        Button {
                            isRegistering.toggle()
                            email = ""
                        } label: {
                            Text(isRegistering ? "Already have an account? Sign in" : "Don't have an account? Register")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .buttonStyle(.plain)
                    }

                    // Biometric login button (if credentials are saved)
                    if keychainService.hasBiometricCredentials() && biometricService.isBiometricAvailable {
                        VStack(spacing: 8) {
                            Text("or")
                                .font(.caption2)
                                .foregroundStyle(.secondary)

                            GlassButton(
                                "Sign in with \(biometricService.biometricType().displayName)",
                                icon: biometricService.biometricType().icon,
                                style: .secondary
                            ) {
                                Task {
                                    await handleBiometricLogin()
                                }
                            }
                            .disabled(authStore.loading)
                        }
                        .padding(.top, 4)
                    }
                }
                .padding(32)
            }
            .frame(width: 450)

            // Loading overlay
            if authStore.loading {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()

                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)
            }
        }
    }

    // MARK: - Auth Handlers

    private func handleAuth() async {
        do {
            let response: LoginResponse

            if isRegistering {
                // Register new user
                response = try await AuthService.shared.register(
                    username: username,
                    password: password
                )
            } else {
                // Login existing user
                response = try await AuthService.shared.login(
                    username: username,
                    password: password
                )

                // Save credentials for biometric login if enabled
                if enableBiometric {
                    do {
                        try keychainService.saveBiometricCredentials(
                            username: username,
                            password: password
                        )
                    } catch {
                        logger.warning("Failed to save biometric credentials: \(error.localizedDescription)")
                    }
                }
            }

            // Save token and trigger bootstrap
            await authStore.saveToken(response.token)

        } catch ApiError.httpError(let code, let data) {
            if let message = String(data: data, encoding: .utf8) {
                await MainActor.run {
                    authStore.setError("Error (\(code)): \(message)")
                }
            } else {
                await MainActor.run {
                    authStore.setError("Error: HTTP \(code)")
                }
            }
        } catch {
            await MainActor.run {
                authStore.setError(error.localizedDescription)
            }
        }
    }

    private func handleBiometricLogin() async {
        do {
            // Authenticate with biometrics
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
            // User cancelled, no error message needed
            return
        } catch {
            await MainActor.run {
                authStore.setError(error.localizedDescription)
            }
        }
    }
}


// MARK: - Preview

#Preview {
    WelcomeView()
        .environment(AuthStore.shared)
        .frame(width: 1200, height: 800)
}
