//
//  VaultLockScreen.swift
//  MagnetarStudio (macOS)
//
//  Vault lock screen with password authentication - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI

struct VaultLockScreen: View {
    @Binding var password: String
    @Binding var showPassword: Bool
    @Binding var authError: String?
    @Binding var isAuthenticating: Bool

    let onUnlock: () -> Void
    let onBiometricAuth: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            // Icon
            Image(systemName: "lock.shield")
                .font(.system(size: 32))
                .foregroundColor(.orange)

            // Title
            VStack(spacing: 8) {
                Text("Unlock Vault")
                    .font(.system(size: 24, weight: .bold))

                Text("Enter your password to access secure files")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            // Password field
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 12) {
                    if showPassword {
                        TextField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    } else {
                        SecureField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }

                    Button {
                        showPassword.toggle()
                    } label: {
                        Image(systemName: showPassword ? "eye.slash" : "eye")
                            .font(.system(size: 18))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(authError != nil ? Color.red : Color.gray.opacity(0.3), lineWidth: 1)
                )

                if let error = authError {
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundColor(.red)
                }
            }

            // Touch ID button (if available)
            Button {
                onBiometricAuth()
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "touchid")
                        .font(.system(size: 18))
                    Text("Use Touch ID")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.primary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)

            // Unlock button
            Button {
                onUnlock()
            } label: {
                HStack(spacing: 8) {
                    if isAuthenticating {
                        ProgressView()
                            .scaleEffect(0.8)
                            .tint(.white)
                    } else {
                        Text("Unlock")
                            .font(.system(size: 14, weight: .medium))
                    }
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(password.isEmpty ? Color.gray : Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
            .disabled(password.isEmpty || isAuthenticating)
        }
        .frame(width: 400)
        .padding(28)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.1), radius: 12, x: 0, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
