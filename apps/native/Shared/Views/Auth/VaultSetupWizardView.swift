//
//  VaultSetupWizardView.swift
//  MagnetarStudio
//
//  Dual-password vault setup wizard (sensitive vs unsensitive)
//

import SwiftUI

struct VaultSetupWizardView: View {
    @Environment(VaultStore.self) private var vaultStore
    @Environment(\.dismiss) private var dismiss

    @State private var currentStep = 0
    @State private var passwordSensitive: String = ""
    @State private var passwordSensitiveConfirm: String = ""
    @State private var passwordUnsensitive: String = ""
    @State private var passwordUnsensitiveConfirm: String = ""
    @State private var isLoading = false
    @State private var errorMessage: String?

    private let totalSteps = 2

    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .ignoresSafeArea()

            LiquidGlassPanel(material: .thick) {
                VStack(spacing: 32) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "lock.shield.fill")
                            .font(.system(size: 48))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("Setup Dual-Password Vault")
                            .font(.title)
                            .fontWeight(.bold)

                        Text("Configure both vault passwords")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    // Progress indicator
                    HStack(spacing: 8) {
                        ForEach(0..<totalSteps, id: \.self) { step in
                            Capsule()
                                .fill(step <= currentStep ? Color.blue : Color.gray.opacity(0.3))
                                .frame(height: 4)
                        }
                    }
                    .padding(.horizontal, 40)

                    // Error message
                    if let errorMessage = errorMessage {
                        Text(errorMessage)
                            .font(.caption)
                            .foregroundColor(.red)
                            .padding(.horizontal, 40)
                    }

                    // Step content
                    stepContent
                        .frame(height: 300)
                        .padding(.horizontal, 40)

                    // Navigation buttons
                    HStack(spacing: 16) {
                        if currentStep > 0 {
                            GlassButton("Back", icon: "chevron.left", style: .secondary) {
                                withAnimation {
                                    currentStep -= 1
                                    errorMessage = nil
                                }
                            }
                            .disabled(isLoading)
                        }

                        Spacer()

                        if currentStep < totalSteps - 1 {
                            GlassButton("Next", icon: "chevron.right", style: .primary) {
                                withAnimation {
                                    if validateCurrentStep() {
                                        currentStep += 1
                                        errorMessage = nil
                                    }
                                }
                            }
                            .disabled(!canProceed || isLoading)
                        } else {
                            GlassButton(isLoading ? "Setting up..." : "Complete Setup", icon: "checkmark", style: .primary) {
                                Task {
                                    await completeSetup()
                                }
                            }
                            .disabled(!canProceed || isLoading)
                        }
                    }
                    .padding(.horizontal, 40)
                }
                .padding(40)
            }
            .frame(width: 600, height: 600)
        }
    }

    // MARK: - Step Content

    @ViewBuilder
    private var stepContent: some View {
        switch currentStep {
        case 0:
            VStack(spacing: 16) {
                Text("Set Sensitive Vault Password")
                    .font(.headline)

                Text("This password protects your sensitive files")
                    .font(.caption)
                    .foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    SecureField("Sensitive vault password", text: $passwordSensitive)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 400)

                    SecureField("Confirm sensitive password", text: $passwordSensitiveConfirm)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 400)

                    // Password strength indicator
                    HStack(spacing: 4) {
                        ForEach(0..<4, id: \.self) { index in
                            Rectangle()
                                .fill(index < passwordStrength(passwordSensitive) ? strengthColor(passwordSensitive) : Color.gray.opacity(0.3))
                                .frame(height: 4)
                        }
                    }
                    .frame(maxWidth: 400)

                    Text(passwordStrengthText(passwordSensitive))
                        .font(.caption2)
                        .foregroundColor(strengthColor(passwordSensitive))
                }

                Text("Minimum 8 characters required")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

        case 1:
            VStack(spacing: 16) {
                Text("Set Unsensitive Vault Password")
                    .font(.headline)

                Text("This password protects your regular files")
                    .font(.caption)
                    .foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    SecureField("Unsensitive vault password", text: $passwordUnsensitive)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 400)

                    SecureField("Confirm unsensitive password", text: $passwordUnsensitiveConfirm)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 400)

                    // Password strength indicator
                    HStack(spacing: 4) {
                        ForEach(0..<4, id: \.self) { index in
                            Rectangle()
                                .fill(index < passwordStrength(passwordUnsensitive) ? strengthColor(passwordUnsensitive) : Color.gray.opacity(0.3))
                                .frame(height: 4)
                        }
                    }
                    .frame(maxWidth: 400)

                    Text(passwordStrengthText(passwordUnsensitive))
                        .font(.caption2)
                        .foregroundColor(strengthColor(passwordUnsensitive))
                }

                Text("Must be different from sensitive password")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

        default:
            EmptyView()
        }
    }

    // MARK: - Validation

    private var canProceed: Bool {
        switch currentStep {
        case 0:
            return passwordSensitive.count >= 8 &&
                   passwordSensitive == passwordSensitiveConfirm
        case 1:
            return passwordUnsensitive.count >= 8 &&
                   passwordUnsensitive == passwordUnsensitiveConfirm &&
                   passwordUnsensitive != passwordSensitive
        default:
            return false
        }
    }

    private func validateCurrentStep() -> Bool {
        switch currentStep {
        case 0:
            if passwordSensitive.count < 8 {
                errorMessage = "Sensitive password must be at least 8 characters"
                return false
            }
            if passwordSensitive != passwordSensitiveConfirm {
                errorMessage = "Passwords do not match"
                return false
            }
            return true
        case 1:
            if passwordUnsensitive.count < 8 {
                errorMessage = "Unsensitive password must be at least 8 characters"
                return false
            }
            if passwordUnsensitive != passwordUnsensitiveConfirm {
                errorMessage = "Passwords do not match"
                return false
            }
            if passwordUnsensitive == passwordSensitive {
                errorMessage = "Unsensitive password must be different from sensitive password"
                return false
            }
            return true
        default:
            return false
        }
    }

    // MARK: - Password Strength

    private func passwordStrength(_ password: String) -> Int {
        if password.isEmpty { return 0 }
        if password.count < 8 { return 1 }

        var strength = 1

        if password.count >= 12 { strength += 1 }
        if password.rangeOfCharacter(from: .uppercaseLetters) != nil &&
           password.rangeOfCharacter(from: .lowercaseLetters) != nil { strength += 1 }
        if password.rangeOfCharacter(from: .decimalDigits) != nil { strength += 1 }

        return min(strength, 4)
    }

    private func passwordStrengthText(_ password: String) -> String {
        switch passwordStrength(password) {
        case 0: return ""
        case 1: return "Weak"
        case 2: return "Fair"
        case 3: return "Good"
        case 4: return "Strong"
        default: return ""
        }
    }

    private func strengthColor(_ password: String) -> Color {
        switch passwordStrength(password) {
        case 0: return .gray
        case 1: return .red
        case 2: return .orange
        case 3: return .yellow
        case 4: return .green
        default: return .gray
        }
    }

    // MARK: - Complete Setup

    private func completeSetup() async {
        isLoading = true
        errorMessage = nil

        do {
            let success = try await VaultService.shared.setupDualPassword(
                passwordSensitive: passwordSensitive,
                passwordUnsensitive: passwordUnsensitive
            )

            if success {
                // Setup complete, dismiss wizard
                dismiss()
            } else {
                errorMessage = "Setup failed - please try again"
            }
        } catch VaultError.invalidRequest(let message) {
            errorMessage = message
        } catch VaultError.unauthorized {
            errorMessage = "Unauthorized - please login again"
        } catch VaultError.serverError(let code) {
            errorMessage = "Server error (HTTP \(code))"
        } catch {
            errorMessage = "Setup failed: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

// MARK: - Preview

#Preview {
    VaultSetupWizardView()
        .environment(VaultStore.shared)
        .frame(width: 1200, height: 800)
}
