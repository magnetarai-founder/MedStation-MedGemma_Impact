//
//  FileAccessPermissionModal.swift
//  MagnetarStudio (macOS)
//
//  CRITICAL: Blocking modal for vault file access permission
//  LIFE OR DEATH for persecuted church - explicit consent required
//
//  Part of Noah's Ark for the Digital Age - Protecting God's people
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "FileAccessPermissionModal")

struct FileAccessPermissionModal: View {
    let request: FileAccessRequest
    let onGrant: (PermissionResponse) async -> Void
    let onDeny: () -> Void
    let onCancel: () -> Void

    @State private var isAuthenticating: Bool = false

    var body: some View {
        VStack(spacing: 24) {
            // Header with security icon
            HStack(spacing: 16) {
                ZStack {
                    Circle()
                        .fill(LinearGradient.magnetarGradient)
                        .frame(width: 64, height: 64)

                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.white)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("File Access Permission Required")
                        .font(.title3)
                        .fontWeight(.bold)

                    Text("Vault: \(request.vaultType.capitalized)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }

            Divider()

            // Request details
            VStack(alignment: .leading, spacing: 16) {
                // Model requesting access
                InfoRow(
                    icon: "cpu",
                    label: "Model",
                    value: request.modelName,
                    color: .blue
                )

                // File being requested
                InfoRow(
                    icon: "doc.fill",
                    label: "File",
                    value: request.fileName,
                    color: .orange
                )

                // File path
                InfoRow(
                    icon: "folder",
                    label: "Path",
                    value: request.filePath,
                    color: .secondary
                )

                // Reason (if provided)
                if let reason = request.reason {
                    InfoRow(
                        icon: "questionmark.circle",
                        label: "Reason",
                        value: reason,
                        color: .purple
                    )
                }

                // Timestamp
                InfoRow(
                    icon: "clock",
                    label: "Requested",
                    value: request.requestedAt.formatted(date: .omitted, time: .shortened),
                    color: .secondary
                )
            }
            .padding(16)
            .background(Color.surfaceSecondary.opacity(0.3))
            .cornerRadius(12)

            // Security notice
            HStack(spacing: 12) {
                Image(systemName: "exclamationmark.shield.fill")
                    .font(.system(size: 20))
                    .foregroundColor(.orange)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Models see metadata only. File contents require permission.")
                        .font(.system(size: 12, weight: .medium))

                    Text("Choose how long to grant access to this file.")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
            }
            .padding(12)
            .background(Color.orange.opacity(0.1))
            .cornerRadius(8)

            Divider()

            // Action buttons
            VStack(spacing: 12) {
                // Just this time (single-use)
                Button {
                    isAuthenticating = true
                    Task {
                        await onGrant(.justThisTime)
                        isAuthenticating = false
                    }
                } label: {
                    HStack {
                        Image(systemName: "checkmark.circle")
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Yes, just this time")
                                .font(.system(size: 13, weight: .semibold))
                            Text("Single-use permission (expires immediately)")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity)
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)
                .disabled(isAuthenticating)

                // For this session (session-scoped)
                Button {
                    isAuthenticating = true
                    Task {
                        await onGrant(.forThisSession)
                        isAuthenticating = false
                    }
                } label: {
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Yes, for this session")
                                .font(.system(size: 13, weight: .semibold))
                            Text("Permission expires when session ends (1 hour)")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)
                .disabled(isAuthenticating)

                // Deny
                Button {
                    onDeny()
                } label: {
                    HStack {
                        Image(systemName: "xmark.circle")
                        VStack(alignment: .leading, spacing: 2) {
                            Text("No, deny access")
                                .font(.system(size: 13, weight: .semibold))
                            Text("Model will not be able to read this file")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity)
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)
                .disabled(isAuthenticating)
            }

            // Cancel button
            HStack {
                Spacer()
                Button("Cancel") {
                    onCancel()
                }
                .keyboardShortcut(.cancelAction)
                .disabled(isAuthenticating)
            }

            // Authenticating indicator
            if isAuthenticating {
                HStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text("Authenticating...")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
                .padding(.top, 8)
            }
        }
        .padding(24)
        .frame(width: 550)
    }
}

// MARK: - Info Row

private struct InfoRow: View {
    let icon: String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundColor(color)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)

                Text(value)
                    .font(.system(size: 13))
                    .lineLimit(2)
            }

            Spacer()
        }
    }
}

// MARK: - Preview

#Preview {
    let mockRequest = FileAccessRequest(
        fileId: "file-123",
        fileName: "sensitive-document.pdf",
        filePath: "/vault/real/documents/sensitive-document.pdf",
        vaultType: "real",
        modelId: "llama3.2:3b",
        modelName: "Llama 3.2 3B",
        sessionId: "session-456",
        requestedAt: Date(),
        reason: "Analyzing document for keyword extraction"
    )

    return FileAccessPermissionModal(
        request: mockRequest,
        onGrant: { scope in
            logger.debug("Granted: \(scope)")
        },
        onDeny: {
            logger.debug("Denied")
        },
        onCancel: {
            logger.debug("Cancelled")
        }
    )
    .frame(width: 550, height: 700)
}
