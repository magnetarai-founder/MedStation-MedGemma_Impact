//
//  TrustComponents.swift
//  MagnetarStudio (macOS)
//
//  Reusable UI components for TrustWorkspace - Extracted for maintainability
//  Part of MagnetarMission: Decentralized trust for churches, missions, and humanitarian teams
//

import SwiftUI

// MARK: - Trust Stat Card (with hover effects)

struct TrustStatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(isHovered ? color : .secondary)
                Text(title)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }
            Text(value)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(isHovered ? color : .primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(isHovered ? color.opacity(0.1) : Color.gray.opacity(0.08))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? color.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Trust Node Row (with hover effects)

struct TrustNodeRow: View {
    let node: TrustNode
    let accentColor: Color
    var onTap: (() -> Void)? = nil
    var onVerify: (() -> Void)? = nil
    var onCopyKey: (() -> Void)? = nil

    @State private var isHovered = false
    @State private var showCopied = false

    private var displayName: String {
        if node.displayMode == .peacetime {
            return node.publicName
        } else {
            return node.alias ?? "Anonymous"
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            // Icon
            Image(systemName: nodeTypeIcon(node.type))
                .font(.system(size: 20))
                .foregroundColor(accentColor)
                .frame(width: 40, height: 40)
                .background(
                    Circle()
                        .fill(accentColor.opacity(isHovered ? 0.25 : 0.15))
                )

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(displayName)
                    .font(.system(size: 14, weight: .medium))

                HStack(spacing: 8) {
                    // Type badge
                    Text(node.type.rawValue.capitalized)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(accentColor)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(accentColor.opacity(0.1))
                        .clipShape(Capsule())

                    if let location = node.location, node.displayMode == .peacetime {
                        HStack(spacing: 4) {
                            Image(systemName: "location")
                                .font(.system(size: 9))
                            Text(location)
                                .font(.system(size: 11))
                        }
                        .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Hover actions
            if isHovered {
                HStack(spacing: 4) {
                    TrustActionButton(icon: "checkmark.shield", help: "Verify", color: .green) {
                        onVerify?()
                    }
                    TrustActionButton(icon: showCopied ? "checkmark" : "doc.on.doc", help: "Copy Key", color: showCopied ? .green : .blue, isSuccess: showCopied) {
                        onCopyKey?()
                        withAnimation { showCopied = true }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            withAnimation { showCopied = false }
                        }
                    }
                    TrustActionButton(icon: "hand.thumbsup", help: "Vouch", color: .purple) {
                        onTap?()
                    }
                }
                .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }

            // Hub badge
            if node.isHub {
                Text("HUB")
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
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(isHovered ? accentColor.opacity(0.08) : Color.gray.opacity(0.06))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(isHovered ? accentColor.opacity(0.3) : accentColor.opacity(0.15), lineWidth: 1)
        )
        .contentShape(Rectangle())
        .onTapGesture {
            onTap?()
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .contextMenu {
            Button {
                onVerify?()
            } label: {
                Label("Verify Safety Number", systemImage: "checkmark.shield")
            }

            Button {
                onTap?()
            } label: {
                Label("Vouch for Node", systemImage: "hand.thumbsup")
            }

            Divider()

            Button {
                onCopyKey?()
            } label: {
                Label("Copy Public Key", systemImage: "doc.on.doc")
            }
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

// MARK: - Trust Action Button

struct TrustActionButton: View {
    let icon: String
    let help: String
    let color: Color
    var isSuccess: Bool = false
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundColor(isSuccess ? .green : (isHovered ? color : .secondary))
                .frame(width: 26, height: 26)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isSuccess ? Color.green.opacity(0.1) : (isHovered ? color.opacity(0.15) : Color.gray.opacity(0.08)))
                )
        }
        .buttonStyle(.plain)
        .help(help)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Form Field Helper

struct TrustFormField<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                Text(title)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.secondary)
            }
            content()
        }
    }
}

// MARK: - Node Type Color Extension

extension NodeType {
    var accentColor: Color {
        switch self {
        case .individual: return .blue
        case .church: return .purple
        case .mission: return .green
        case .family: return .orange
        case .organization: return .cyan
        }
    }
}
