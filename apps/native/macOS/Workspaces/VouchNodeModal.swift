//
//  VouchNodeModal.swift
//  MagnetarStudio (macOS)
//
//  Modal for vouching for a node in MagnetarTrust network
//  Extracted from TrustWorkspace.swift for better code organization
//

import SwiftUI

struct VouchNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let node: TrustNode
    let onVouched: () -> Void

    @State private var trustLevel: TrustLevel = .vouched
    @State private var note: String = ""
    @State private var isVouching: Bool = false
    @State private var errorMessage: String? = nil
    @State private var showSafetyNumberVerification: Bool = false
    @State private var isVerified: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Vouch for \(node.publicName)")
                        .font(.system(size: 20, weight: .bold))
                    Text("Create a trust relationship")
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

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Node info
                    HStack(spacing: 12) {
                        Image(systemName: nodeTypeIcon(node.type))
                            .font(.system(size: 24))
                            .foregroundColor(.magnetarPrimary)
                            .frame(width: 48, height: 48)
                            .background(
                                Circle()
                                    .fill(Color.magnetarPrimary.opacity(0.15))
                            )

                        VStack(alignment: .leading, spacing: 4) {
                            Text(node.publicName)
                                .font(.system(size: 16, weight: .medium))
                            Text(node.type.rawValue.capitalized)
                                .font(.system(size: 13))
                                .foregroundColor(.secondary)
                            if let location = node.location {
                                Text(location)
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                        }

                        Spacer()

                        // Verification status
                        if isVerified {
                            HStack(spacing: 4) {
                                Image(systemName: "checkmark.shield.fill")
                                Text("Verified")
                            }
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.green)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(
                                Capsule()
                                    .fill(Color.green.opacity(0.15))
                            )
                        }
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.gray.opacity(0.05))
                    )

                    // Safety Number Verification
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Image(systemName: "checkmark.shield")
                                .foregroundColor(.secondary)
                            Text("Identity Verification")
                                .font(.system(size: 13, weight: .medium))
                                .foregroundColor(.secondary)
                        }

                        Button {
                            showSafetyNumberVerification = true
                        } label: {
                            HStack {
                                Image(systemName: isVerified ? "checkmark.shield.fill" : "shield.lefthalf.filled")
                                    .foregroundColor(isVerified ? .green : .magnetarPrimary)
                                Text(isVerified ? "View Safety Number" : "Verify Safety Number")
                                    .font(.system(size: 14))
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                            .padding(12)
                            .background(
                                RoundedRectangle(cornerRadius: 10)
                                    .stroke(isVerified ? Color.green.opacity(0.5) : Color.magnetarPrimary.opacity(0.3), lineWidth: 1)
                                    .background(
                                        RoundedRectangle(cornerRadius: 10)
                                            .fill(isVerified ? Color.green.opacity(0.05) : Color.magnetarPrimary.opacity(0.05))
                                    )
                            )
                        }
                        .buttonStyle(.plain)

                        if !isVerified {
                            Text("Compare safety numbers with \(node.publicName) to verify identity")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                    }

                    // Trust Level
                    FormField(title: "Trust Level *", icon: "hand.thumbsup") {
                        VStack(spacing: 12) {
                            trustLevelOption(
                                level: .direct,
                                title: "Direct Trust",
                                description: "I know this person/organization personally",
                                color: .green
                            )
                            trustLevelOption(
                                level: .vouched,
                                title: "Vouched",
                                description: "I vouch for this node based on recommendation",
                                color: .blue
                            )
                        }
                    }

                    // Note
                    FormField(title: "Note (Optional)", icon: "note.text") {
                        TextEditor(text: $note)
                            .frame(height: 100)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
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
                        await vouchForNode()
                    }
                } label: {
                    if isVouching {
                        ProgressView()
                            .scaleEffect(0.8)
                            .frame(width: 100)
                    } else {
                        Text("Vouch")
                            .frame(width: 100)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isVouching)
            }
            .padding(24)
        }
        .frame(width: 500, height: 620)
        .sheet(isPresented: $showSafetyNumberVerification) {
            SafetyNumberVerificationModal(
                node: node,
                onVerified: {
                    isVerified = true
                }
            )
        }
    }

    private func trustLevelOption(level: TrustLevel, title: String, description: String, color: Color) -> some View {
        Button {
            trustLevel = level
        } label: {
            HStack(spacing: 12) {
                Image(systemName: trustLevel == level ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 20))
                    .foregroundColor(trustLevel == level ? color : .secondary)

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.primary)
                    Text(description)
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(trustLevel == level ? color : Color.gray.opacity(0.3), lineWidth: trustLevel == level ? 2 : 1)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(trustLevel == level ? color.opacity(0.05) : Color.clear)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    private func vouchForNode() async {
        isVouching = true
        errorMessage = nil
        defer { isVouching = false }

        do {
            let request = VouchRequest(
                targetNodeId: node.id,
                level: trustLevel,
                note: note.isEmpty ? nil : note
            )

            let relationship = try await TrustService.shared.vouchForNode(request)
            print("✅ Vouched for \(node.publicName): \(relationship.id)")
            onVouched()
            dismiss()
        } catch {
            errorMessage = "Failed to vouch: \(error.localizedDescription)"
            print("❌ Vouching failed: \(error)")
        }
    }

    private func nodeTypeIcon(_ type: NodeType) -> String {
        switch type {
        case .individual: return "person"
        case .church: return "building.columns"
        case .mission: return "globe"
        case .family: return "person.3"
        case .organization: return "building.2"
        }
    }
}

#if DEBUG
#Preview {
    VouchNodeModal(
        node: TrustNode(
            id: "preview",
            publicKey: "key",
            publicName: "Preview Church",
            alias: nil,
            type: .church,
            displayMode: .peacetime,
            bio: nil,
            location: "New York, USA",
            createdAt: "2024-01-01",
            lastSeen: "2024-01-01",
            isHub: false,
            vouchedBy: nil
        ),
        onVouched: {}
    )
}
#endif
