//
//  SecuritySettingsView.swift
//  MagnetarStudio
//
//  Settings panel for security configuration.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SecuritySettingsView")

// MARK: - Security Settings

struct SecuritySettingsView: View {
    @Binding var enableBiometrics: Bool
    @AppStorage("autoLockEnabled") private var autoLockEnabled = true
    @AppStorage("autoLockTimeout") private var autoLockTimeout = 15
    @State private var cacheStatus: SimpleStatus = .idle
    @State private var keychainStatus: SimpleStatus = .idle
    @State private var biometricStatus: SimpleStatus = .idle

    private let biometricService = BiometricAuthService.shared
    private let keychainService = KeychainService.shared
    @State private var securityManager = SecurityManager.shared

    var body: some View {
        Form {
            Section("Network Firewall") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Enable Network Firewall", isOn: Binding(
                        get: { securityManager.networkFirewallEnabled },
                        set: { securityManager.setNetworkFirewall(enabled: $0) }
                    ))

                    Text("Control all outgoing network connections with approval prompts (Little Snitch-style)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if securityManager.networkFirewallEnabled {
                        HStack {
                            Image(systemName: "shield.fill")
                                .foregroundStyle(.green)
                            Text("Firewall active - all requests require approval")
                                .font(.caption)
                                .foregroundStyle(.green)
                        }
                        .padding(.top, 4)
                    }
                }
            }

            Section("Biometric Authentication") {
                HStack {
                    Image(systemName: biometricService.biometricType().icon)
                        .foregroundStyle(.blue)
                    Text(biometricService.biometricType().displayName)
                        .font(.headline)
                }

                Toggle("Enable Biometric Login", isOn: $enableBiometrics)
                    .disabled(!biometricService.isBiometricAvailable)

                Text("Sign in quickly and securely using \(biometricService.biometricType().displayName)")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if keychainService.hasBiometricCredentials() {
                    VStack(spacing: 8) {
                        HStack {
                            Image(systemName: "checkmark.shield.fill")
                                .foregroundStyle(.green)
                            Text("Biometric credentials stored")
                                .font(.caption)
                            Spacer()
                        }

                        Button(role: .destructive) {
                            clearBiometricCredentials()
                        } label: {
                            HStack {
                                Image(systemName: "trash")
                                Text("Remove Biometric Credentials")
                            }
                        }
                        .disabled(biometricStatus == .loading)

                        statusLabel(biometricStatus)
                    }
                }
            }

            Section("Session") {
                Toggle("Auto-lock after Inactivity", isOn: $autoLockEnabled)

                Picker("Timeout", selection: $autoLockTimeout) {
                    Text("5 minutes").tag(5)
                    Text("15 minutes").tag(15)
                    Text("30 minutes").tag(30)
                    Text("1 hour").tag(60)
                }
                .disabled(!autoLockEnabled)
            }

            Section("Data") {
                Button("Clear Cache") {
                    Task { await clearCache() }
                }
                statusLabel(cacheStatus)

                Button("Reset Keychain", role: .destructive) {
                    Task { await resetKeychain() }
                }
                statusLabel(keychainStatus)
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Actions

    private func clearCache() async {
        await MainActor.run { cacheStatus = .loading }

        do {
            let fileManager = FileManager.default
            let cachesDir = try fileManager.url(
                for: .cachesDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: true
            )

            let bundleId = Bundle.main.bundleIdentifier ?? "com.magnetarstudio.app"
            let appCacheDir = cachesDir.appendingPathComponent(bundleId, isDirectory: true)

            if fileManager.fileExists(atPath: appCacheDir.path) {
                let contents = try fileManager.contentsOfDirectory(at: appCacheDir, includingPropertiesForKeys: nil)
                var failures = 0
                for item in contents {
                    do {
                        try fileManager.removeItem(at: item)
                    } catch {
                        failures += 1
                        logger.warning("Failed to remove cache item \(item.lastPathComponent): \(error)")
                    }
                }
                if failures > 0 {
                    logger.warning("\(failures) cache items could not be removed")
                }
            }

            await MainActor.run { cacheStatus = .success("Cache cleared") }
        } catch {
            await MainActor.run { cacheStatus = .failure(error.localizedDescription) }
        }
    }

    private func resetKeychain() async {
        await MainActor.run { keychainStatus = .loading }

        do {
            try KeychainService.shared.deleteToken()
            await MainActor.run { keychainStatus = .success("Keychain reset") }
        } catch {
            await MainActor.run { keychainStatus = .failure(error.localizedDescription) }
        }
    }

    private func clearBiometricCredentials() {
        biometricStatus = .loading

        do {
            try keychainService.deleteBiometricCredentials()
            biometricStatus = .success("Biometric credentials removed")
        } catch {
            biometricStatus = .failure(error.localizedDescription)
        }
    }
}
