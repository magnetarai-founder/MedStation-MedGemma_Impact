//
//  NetworkApprovalModal.swift
//  MagnetarStudio
//
//  Modal for approving/denying network connection requests
//  Part of Little Snitch-style network firewall
//

import SwiftUI

struct NetworkApprovalModal: View {
    let request: URLRequest
    let onApprove: (Bool) -> Void // Bool = permanently
    let onDeny: (Bool) -> Void    // Bool = permanently

    @State private var approvalMode: ApprovalMode = .block
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient.magnetarGradient
                .opacity(0.3)
                .ignoresSafeArea()

            LiquidGlassPanel(material: .thick) {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "network")
                            .font(.system(size: 40))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("Network Connection Request")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text("MagnetarStudio wants to connect")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    Divider()

                    // Request details
                    VStack(alignment: .leading, spacing: 12) {
                        NetworkDetailRow(label: "Domain", value: request.url?.host ?? "Unknown")
                        NetworkDetailRow(label: "Endpoint", value: request.url?.path ?? "/")
                        NetworkDetailRow(label: "Protocol", value: request.url?.scheme?.uppercased() ?? "HTTP")
                        NetworkDetailRow(label: "Method", value: request.httpMethod ?? "GET")

                        if let purpose = inferPurpose(from: request) {
                            NetworkDetailRow(label: "Purpose", value: purpose)
                        }
                    }
                    .padding(.horizontal, 8)

                    Divider()

                    // Approval options
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Action")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        VStack(spacing: 8) {
                            ApprovalOption(
                                mode: .allowOnce,
                                selected: approvalMode == .allowOnce,
                                onSelect: { approvalMode = .allowOnce }
                            )

                            ApprovalOption(
                                mode: .allowAlways,
                                selected: approvalMode == .allowAlways,
                                onSelect: { approvalMode = .allowAlways }
                            )

                            ApprovalOption(
                                mode: .block,
                                selected: approvalMode == .block,
                                onSelect: { approvalMode = .block }
                            )

                            ApprovalOption(
                                mode: .blockAlways,
                                selected: approvalMode == .blockAlways,
                                onSelect: { approvalMode = .blockAlways }
                            )
                        }
                    }

                    // Action buttons
                    HStack(spacing: 12) {
                        GlassButton("Cancel", icon: "xmark", style: .secondary) {
                            onDeny(false)
                            dismiss()
                        }

                        Spacer()

                        GlassButton("Confirm", icon: "checkmark", style: .primary) {
                            handleConfirm()
                            dismiss()
                        }
                    }
                }
                .padding(32)
            }
            .frame(width: 500, height: 550)
        }
    }

    // MARK: - Helpers

    private func handleConfirm() {
        switch approvalMode {
        case .allowOnce:
            onApprove(false)
        case .allowAlways:
            onApprove(true)
        case .block:
            onDeny(false)
        case .blockAlways:
            onDeny(true)
        }
    }

    private func inferPurpose(from request: URLRequest) -> String? {
        guard let path = request.url?.path else { return nil }

        if path.contains("/models") {
            return "Download AI model"
        } else if path.contains("/chat") {
            return "Send chat message"
        } else if path.contains("/vault") {
            return "Access encrypted vault"
        } else if path.contains("/auth") {
            return "User authentication"
        } else if path.contains("/team") {
            return "Team collaboration"
        }

        return nil
    }
}

// MARK: - Supporting Views

struct NetworkDetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .top) {
            Text(label + ":")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.secondary)
                .frame(width: 80, alignment: .leading)

            Text(value)
                .font(.caption)
                .foregroundColor(.primary)

            Spacer()
        }
    }
}

struct ApprovalOption: View {
    let mode: ApprovalMode
    let selected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 12) {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundColor(selected ? .blue : .gray)
                    .font(.system(size: 16))

                VStack(alignment: .leading, spacing: 2) {
                    Text(mode.title)
                        .font(.subheadline)
                        .fontWeight(.medium)

                    Text(mode.description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(selected ? Color.blue.opacity(0.1) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(selected ? Color.blue : Color.gray.opacity(0.3), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Supporting Types

enum ApprovalMode {
    case allowOnce
    case allowAlways
    case block
    case blockAlways

    var title: String {
        switch self {
        case .allowOnce: return "Allow Once"
        case .allowAlways: return "Allow Always"
        case .block: return "Block"
        case .blockAlways: return "Block Always"
        }
    }

    var description: String {
        switch self {
        case .allowOnce: return "Permit this request only"
        case .allowAlways: return "Add domain to allowlist"
        case .block: return "Deny this request (default)"
        case .blockAlways: return "Add domain to blocklist"
        }
    }
}
