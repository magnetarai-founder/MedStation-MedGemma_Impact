//
//  WelcomeView.swift
//  MagnetarStudio
//
//  Login/Register screen shown when authState == .welcome
//

import SwiftUI

struct WelcomeView: View {
    @EnvironmentObject private var authStore: AuthStore

    @State private var username: String = ""
    @State private var password: String = ""
    @State private var email: String = ""
    @State private var isRegistering: Bool = false

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
                    if let error = authStore.error {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
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

                        Button {
                            isRegistering.toggle()
                            email = ""
                        } label: {
                            Text(isRegistering ? "Already have an account? Sign in" : "Don't have an account? Register")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .buttonStyle(.plain)
                    }

                    // Biometric info (if available)
                    if KeychainService.shared.loadToken() != nil {
                        HStack(spacing: 8) {
                            Image(systemName: "lock.shield")
                                .font(.caption)
                            Text("Your credentials are securely stored")
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
            if authStore.loading {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()

                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)
            }
        }
    }

    // MARK: - Auth Handler

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
}

// MARK: - Preview

#Preview {
    WelcomeView()
        .environmentObject(AuthStore.shared)
        .frame(width: 1200, height: 800)
}
