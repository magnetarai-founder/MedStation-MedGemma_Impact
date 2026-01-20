//
//  VaultLockScreen.swift
//  MagnetarStudio (macOS)
//
//  Vault lock screen with password authentication - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//  Enhanced with gradient icon and hover effects
//

import SwiftUI

struct VaultLockScreen: View {
    @Binding var password: String
    @Binding var showPassword: Bool
    @Binding var authError: String?
    @Binding var isAuthenticating: Bool

    let onUnlock: () -> Void
    let onBiometricAuth: () -> Void

    @State private var isTouchIDHovered = false
    @State private var isUnlockHovered = false

    var body: some View {
        VStack(spacing: 24) {
            // Icon with gradient background
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [.orange.opacity(0.2), .yellow.opacity(0.1)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 70, height: 70)

                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.orange, .yellow],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            }

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
                .foregroundColor(isTouchIDHovered ? .primary : .secondary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isTouchIDHovered ? Color.gray.opacity(0.1) : Color.clear)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(isTouchIDHovered ? Color.primary.opacity(0.3) : Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
            .onHover { hovering in
                withAnimation(.easeInOut(duration: 0.15)) {
                    isTouchIDHovered = hovering
                }
            }

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
                        Image(systemName: "lock.open")
                            .font(.system(size: 14))
                        Text("Unlock")
                            .font(.system(size: 14, weight: .medium))
                    }
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(password.isEmpty ? Color.gray : (isUnlockHovered ? Color.magnetarPrimary.opacity(0.9) : Color.magnetarPrimary))
                )
                .scaleEffect(isUnlockHovered && !password.isEmpty ? 1.02 : 1.0)
            }
            .buttonStyle(.plain)
            .disabled(password.isEmpty || isAuthenticating)
            .onHover { hovering in
                withAnimation(.easeInOut(duration: 0.15)) {
                    isUnlockHovered = hovering
                }
            }
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
