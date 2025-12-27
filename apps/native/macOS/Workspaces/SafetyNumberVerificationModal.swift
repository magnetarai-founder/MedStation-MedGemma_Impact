//
//  SafetyNumberVerificationModal.swift
//  MagnetarStudio (macOS)
//
//  Safety Number Verification UI for MagnetarTrust
//  Allows users to verify node identity by comparing safety numbers out-of-band
//
//  SECURITY (Dec 2025):
//  - Safety numbers detect MITM attacks on key exchange
//  - Both parties see the same 60-digit number
//  - Verification should happen in person, via phone, or trusted channel
//

import SwiftUI

struct SafetyNumberVerificationModal: View {
    @Environment(\.dismiss) private var dismiss
    let node: TrustNode
    let onVerified: () -> Void

    @State private var safetyNumber: String = ""
    @State private var safetyNumberGrid: [[String]] = []
    @State private var fingerprint: String = ""
    @State private var isVerifying: Bool = false
    @State private var showCopiedAlert: Bool = false

    private let trustService = TrustService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header
                .padding(24)

            Divider()

            // Content
            ScrollView {
                VStack(spacing: 24) {
                    // Node info card
                    nodeInfoCard

                    // Safety number section
                    safetyNumberSection

                    // Fingerprint section
                    fingerprintSection

                    // Instructions
                    instructionsSection
                }
                .padding(24)
            }

            Divider()

            // Footer
            footer
                .padding(24)
        }
        .frame(width: 520, height: 680)
        .onAppear {
            loadSafetyNumber()
        }
        .alert("Copied to Clipboard", isPresented: $showCopiedAlert) {
            Button("OK", role: .cancel) {}
        } message: {
            Text("Safety number copied. Share via a trusted channel to verify.")
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.shield")
                        .font(.system(size: 20))
                        .foregroundColor(.magnetarPrimary)
                    Text("Verify Safety Number")
                        .font(.system(size: 20, weight: .bold))
                }
                Text("Compare with \(node.publicName) to verify identity")
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
    }

    // MARK: - Node Info Card

    private var nodeInfoCard: some View {
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
                HStack(spacing: 8) {
                    Text(node.type.rawValue.capitalized)
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                    if let location = node.location {
                        Text("•")
                            .foregroundColor(.secondary)
                        Text(location)
                            .font(.system(size: 13))
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Verification status badge
            if node.displayMode == .underground {
                Text("UNDERGROUND")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(Color.orange.opacity(0.2))
                    )
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.gray.opacity(0.05))
        )
    }

    // MARK: - Safety Number Section

    private var safetyNumberSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "number.square")
                    .foregroundColor(.secondary)
                Text("Safety Number")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
                Button {
                    copyToClipboard(safetyNumber)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "doc.on.doc")
                        Text("Copy")
                    }
                    .font(.system(size: 12))
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)
            }

            // Grid display (like Signal)
            VStack(spacing: 8) {
                ForEach(safetyNumberGrid.indices, id: \.self) { rowIndex in
                    HStack(spacing: 16) {
                        ForEach(safetyNumberGrid[rowIndex].indices, id: \.self) { colIndex in
                            Text(safetyNumberGrid[rowIndex][colIndex])
                                .font(.system(size: 18, weight: .medium, design: .monospaced))
                                .foregroundColor(.primary)
                        }
                    }
                }
            }
            .padding(20)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.gray.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.magnetarPrimary.opacity(0.3), lineWidth: 2)
                    )
            )

            Text("If you and \(node.publicName) see the same number, your connection is secure.")
                .font(.system(size: 12))
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Fingerprint Section

    private var fingerprintSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "key")
                    .foregroundColor(.secondary)
                Text("Key Fingerprint")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
                Button {
                    copyToClipboard(fingerprint)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "doc.on.doc")
                        Text("Copy")
                    }
                    .font(.system(size: 12))
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)
            }

            Text(fingerprint)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(.secondary)
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.gray.opacity(0.05))
                )
        }
    }

    // MARK: - Instructions Section

    private var instructionsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "info.circle")
                    .foregroundColor(.blue)
                Text("How to Verify")
                    .font(.system(size: 14, weight: .semibold))
            }

            VStack(alignment: .leading, spacing: 8) {
                instructionRow(number: "1", text: "Meet in person, call, or use a trusted channel")
                instructionRow(number: "2", text: "Both parties open this screen for each other")
                instructionRow(number: "3", text: "Compare the safety numbers - they must match")
                instructionRow(number: "4", text: "If they match, tap 'Mark as Verified'")
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.blue.opacity(0.05))
            )

            // Warning
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "exclamationmark.triangle")
                    .foregroundColor(.orange)
                Text("If the numbers don't match, do not proceed. This could indicate a security issue or man-in-the-middle attack.")
                    .font(.system(size: 12))
                    .foregroundColor(.orange)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.orange.opacity(0.1))
            )
        }
    }

    private func instructionRow(number: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text(number)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundColor(.white)
                .frame(width: 20, height: 20)
                .background(Circle().fill(Color.blue))

            Text(text)
                .font(.system(size: 13))
                .foregroundColor(.primary)
        }
    }

    // MARK: - Footer

    private var footer: some View {
        HStack {
            Button("Cancel") {
                dismiss()
            }
            .buttonStyle(.bordered)

            Spacer()

            Button {
                markAsVerified()
            } label: {
                HStack(spacing: 6) {
                    if isVerifying {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Image(systemName: "checkmark.shield.fill")
                    }
                    Text("Mark as Verified")
                }
                .frame(width: 160)
            }
            .buttonStyle(.borderedProminent)
            .disabled(isVerifying)
        }
    }

    // MARK: - Actions

    private func loadSafetyNumber() {
        if let number = trustService.generateSafetyNumber(forNode: node) {
            safetyNumber = number
            safetyNumberGrid = trustService.formatSafetyNumberGrid(number)
        }
        fingerprint = trustService.generateFingerprint(publicKey: node.publicKey)
    }

    private func copyToClipboard(_ text: String) {
        #if os(macOS)
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        #endif
        showCopiedAlert = true
    }

    private func markAsVerified() {
        isVerifying = true

        // In a full implementation, this would:
        // 1. Store the verified status locally
        // 2. Optionally notify the backend
        // For now, we just call the callback

        Task {
            try? await Task.sleep(for: .milliseconds(500))
            isVerifying = false
            onVerified()
            dismiss()
        }
    }

    // MARK: - Helpers

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

// MARK: - Preview

#if DEBUG
#Preview {
    SafetyNumberVerificationModal(
        node: TrustNode(
            id: "preview",
            publicKey: "dGVzdC1wdWJsaWMta2V5LWJhc2U2NC1lbmNvZGVk",
            publicName: "Preview Church",
            alias: nil,
            type: .church,
            displayMode: .peacetime,
            bio: "A test church for preview",
            location: "New York, USA",
            createdAt: "2024-01-01",
            lastSeen: "2024-01-01",
            isHub: true,
            vouchedBy: nil
        ),
        onVerified: { print("Verified!") }
    )
}
#endif
