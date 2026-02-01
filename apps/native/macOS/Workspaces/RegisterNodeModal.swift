//
//  RegisterNodeModal.swift
//  MagnetarStudio (macOS)
//
//  Modal for registering a new trust node in MagnetarTrust network
//  Extracted from TrustWorkspace.swift for better code organization
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "RegisterNodeModal")

struct RegisterNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let onRegister: (TrustNode) -> Void

    @State private var publicName: String = ""
    @State private var alias: String = ""
    @State private var nodeType: NodeType = .individual
    @State private var bio: String = ""
    @State private var location: String = ""
    @State private var displayMode: DisplayMode = .peacetime
    @State private var generatedPublicKey: String = ""

    @State private var isRegistering: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Register Trust Node")
                        .font(.system(size: 20, weight: .bold))
                    Text("Join the MagnetarTrust network")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(24)

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Public Name
                    FormField(title: "Public Name *", icon: "person") {
                        TextField("Your name or church name", text: $publicName)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Node Type
                    FormField(title: "Type *", icon: "building.columns") {
                        Picker("", selection: $nodeType) {
                            ForEach([NodeType.individual, .church, .mission, .family, .organization], id: \.self) { type in
                                Text(type.rawValue.capitalized).tag(type)
                            }
                        }
                        .pickerStyle(.segmented)
                    }

                    // Alias (Underground mode)
                    FormField(title: "Alias (Underground Mode)", icon: "theatermasks") {
                        TextField("Pseudonym or code name", text: $alias)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Display Mode
                    FormField(title: "Display Mode *", icon: "eye") {
                        Picker("", selection: $displayMode) {
                            Text("Peacetime").tag(DisplayMode.peacetime)
                            Text("Underground").tag(DisplayMode.underground)
                        }
                        .pickerStyle(.segmented)
                    }

                    // Bio
                    FormField(title: "Bio", icon: "doc.text") {
                        TextEditor(text: $bio)
                            .frame(height: 80)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
                    }

                    // Location
                    FormField(title: "Location", icon: "location") {
                        TextField("City, Country", text: $location)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Public Key (Generated)
                    FormField(title: "Public Key", icon: "key") {
                        HStack {
                            Text(generatedPublicKey.isEmpty ? "Will be generated on save" : generatedPublicKey)
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                            Spacer()
                            if !generatedPublicKey.isEmpty {
                                Button {
                                    generateKeys()
                                } label: {
                                    Image(systemName: "arrow.clockwise")
                                }
                                .buttonStyle(.plain)
                                .help("Regenerate keys")
                            }
                        }
                        .padding(8)
                        .background(Color.gray.opacity(0.05))
                        .cornerRadius(6)
                    }

                    if let error = errorMessage {
                        Text(error)
                            .font(.system(size: 13))
                            .foregroundColor(.red)
                            .padding(12)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.red.opacity(0.1))
                            )
                    }
                }
                .padding(24)
            }

            Divider()

            // Footer
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)

                Spacer()

                Button {
                    Task {
                        await registerNode()
                    }
                } label: {
                    if isRegistering {
                        ProgressView()
                            .scaleEffect(0.8)
                            .frame(width: 100)
                    } else {
                        Text("Register")
                            .frame(width: 100)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isRegistering || publicName.isEmpty)
            }
            .padding(24)
        }
        .frame(width: 600, height: 700)
        .onAppear {
            generateKeys()
        }
    }

    private func generateKeys() {
        // Use proper ECDSA P-256 cryptographic key generation via TrustKeyManager
        // Keys are stored securely in the Keychain with Secure Enclave attributes
        do {
            // Generate new key pair (stored in Keychain)
            _ = try TrustKeyManager.shared.generateKeyPair()
            // Get the public key as base64 for display and registration
            generatedPublicKey = try TrustKeyManager.shared.getPublicKeyBase64()
        } catch {
            // Fall back to displaying error - don't silently fail on crypto
            errorMessage = "Failed to generate cryptographic keys: \(error.localizedDescription)"
            generatedPublicKey = ""
        }
    }

    private func registerNode() async {
        isRegistering = true
        errorMessage = nil
        defer { isRegistering = false }

        do {
            // Get the private key for signing the registration request
            let privateKey = try TrustKeyManager.shared.getPrivateKey()

            let request = try RegisterNodeRequest(
                privateKey: privateKey,
                publicName: publicName,
                type: nodeType,
                alias: alias.isEmpty ? nil : alias,
                bio: bio.isEmpty ? nil : bio,
                location: location.isEmpty ? nil : location,
                displayMode: displayMode
            )

            let node = try await TrustService.shared.registerNode(request)
            logger.info("Node registered: \(node.id)")
            onRegister(node)
            dismiss()
        } catch {
            errorMessage = "Failed to register: \(error.localizedDescription)"
            logger.error("Registration failed: \(error)")
        }
    }
}

// MARK: - Form Field Helper

private struct FormField<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
            content()
        }
    }
}

#if DEBUG
#Preview {
    RegisterNodeModal(onRegister: { _ in })
}
#endif
