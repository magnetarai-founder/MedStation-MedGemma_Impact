//
//  PanicModeSheet.swift
//  MagnetarStudio
//
//  Panic Mode modal for emergency security - Extracted from Header.swift
//

import SwiftUI

struct PanicModeSheet: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var vaultStore = VaultStore.shared

    @State private var isExecuting = false
    @State private var shouldQuitApp = false

    var body: some View {
        VStack(spacing: 24) {
            // Close button
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.secondary)
                        .padding(8)
                        .background(Color.secondary.opacity(0.1))
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .help("Close")
            }
            .padding(.horizontal, 24)
            .padding(.top, 16)

            // Warning Icon
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 64))
                .foregroundColor(.red)

            // Title
            Text("Panic Mode")
                .font(.system(size: 24, weight: .bold))

            // Description
            VStack(spacing: 12) {
                Text("Emergency Security Protocol")
                    .font(.system(size: 16, weight: .semibold))

                Text("This will immediately:")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    SecurityActionRow(icon: "lock.fill", text: "Lock all vaults")
                    SecurityActionRow(icon: "arrow.right.square.fill", text: "Log out of your account")
                    SecurityActionRow(icon: "trash.fill", text: "Clear sensitive data from memory")
                    SecurityActionRow(icon: "xmark.circle.fill", text: "Optionally quit the application")
                }
                .padding()
                .background(Color.red.opacity(0.1))
                .cornerRadius(12)
            }

            // Quit App Option
            Toggle(isOn: $shouldQuitApp) {
                HStack {
                    Image(systemName: "power")
                        .foregroundColor(.red)
                    Text("Quit application after panic")
                        .font(.system(size: 14, weight: .medium))
                }
            }
            .toggleStyle(.checkbox)
            .padding(.horizontal, 40)

            Spacer()

            // Action Buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)
                .keyboardShortcut(.cancelAction)

                Button(action: executePanicMode) {
                    HStack {
                        if isExecuting {
                            ProgressView()
                                .scaleEffect(0.7)
                                .frame(width: 14, height: 14)
                        } else {
                            Image(systemName: "exclamationmark.triangle.fill")
                        }
                        Text(isExecuting ? "Executing..." : "Execute Panic Mode")
                    }
                    .frame(minWidth: 180)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
                .disabled(isExecuting)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.bottom, 24)
        }
        .frame(width: 480, height: 560)
    }

    private func executePanicMode() {
        isExecuting = true

        Task { @MainActor in
            do {
                // 1. Trigger backend panic mode (secure wipe)
                let response = try await PanicModeService.shared.triggerPanicMode(
                    level: .standard,
                    reason: "User-initiated panic from macOS app"
                )

                print("✅ Panic mode triggered successfully")
                print("   Actions taken: \(response.actionsTaken.joined(separator: ", "))")

                if !response.errors.isEmpty {
                    print("⚠️ Panic mode completed with errors:")
                    response.errors.forEach { print("   - \($0)") }
                }

                // 2. Lock all vaults locally
                vaultStore.lock()

                // 3. Clear database sessions
                NotificationCenter.default.post(name: .init("DatabaseWorkspaceClearWorkspace"), object: nil)

                // 4. Logout (clears token and sensitive data)
                await authStore.logout()

                // 5. Quit app if requested
                if shouldQuitApp {
                    try? await Task.sleep(nanoseconds: 300_000_000) // 0.3 seconds
                    NSApplication.shared.terminate(nil)
                }

                dismiss()

            } catch PanicModeError.rateLimitExceeded {
                print("❌ Panic mode rate limit exceeded")
                // Still perform local cleanup
                vaultStore.lock()
                await authStore.logout()
                if shouldQuitApp {
                    NSApplication.shared.terminate(nil)
                }
                dismiss()

            } catch {
                print("❌ Panic mode backend error: \(error.localizedDescription)")
                // Still perform local cleanup even if backend fails
                vaultStore.lock()
                await authStore.logout()
                if shouldQuitApp {
                    NSApplication.shared.terminate(nil)
                }
                dismiss()
            }
        }
    }
}
