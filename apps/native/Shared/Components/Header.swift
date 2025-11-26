//
//  Header.swift
//  MagnetarStudio
//
//  Global header bar with a lighter, Xcode-like toolbar aesthetic
//  - Soft glass gradient background with subtle chroma
//  - Left: App glyph + title (no star/pill noise)
//  - Right: Condensed controls (terminal, activity, panic)
//

import SwiftUI

struct Header: View {
    @State private var showTerminals = false
    @State private var showPanicMode = false
    @State private var terminalCount = 0

    var body: some View {
        ZStack(alignment: .center) {
            // Background: muted glass gradient with a faint chroma sweep
            LinearGradient(
                colors: [
                    Color(red: 0.11, green: 0.13, blue: 0.18).opacity(0.92),
                    Color(red: 0.08, green: 0.09, blue: 0.14).opacity(0.94)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .overlay(
                LinearGradient(
                    colors: [
                        Color.magnetarPrimary.opacity(0.18),
                        Color.magnetarSecondary.opacity(0.12)
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .blur(radius: 36)
            )
            .background(.regularMaterial)
            .ignoresSafeArea(edges: .top)

            // Content
            HStack(alignment: .center, spacing: 16) {
                BrandCluster()

                Spacer()

                ControlCluster(
                    terminalCount: terminalCount,
                    showTerminals: $showTerminals,
                    showPanicMode: $showPanicMode
                )
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
        }
        .frame(height: 54)
        .overlay(
            Rectangle()
                .fill(Color.white.opacity(0.12))
                .frame(height: 1),
            alignment: .bottom
        )
    }
}

// MARK: - Subcomponents

private struct BrandCluster: View {
    var body: some View {
        Text("MagnetarStudio")
            .font(.system(size: 22, weight: .bold))
            .foregroundColor(.primary)
    }
}

private struct ControlCluster: View {
    let terminalCount: Int
    @Binding var showTerminals: Bool
    @Binding var showPanicMode: Bool

    var body: some View {
        HStack(spacing: 10) {
            HeaderToolbarButton(icon: "terminal", label: "\(terminalCount)") {
                showTerminals = true
            }
            .help("Terminals")

            HeaderToolbarButton(icon: "chart.bar.fill") {
                // Show activity
            }
            .help("Activity")

            HeaderToolbarButton(
                icon: "exclamationmark.triangle.fill",
                tint: Color.red.opacity(0.9),
                background: Color.red.opacity(0.12)
            ) {
                showPanicMode = true
            }
            .help("Panic Mode")
        }
    }
}

private struct HeaderToolbarButton: View {
    let icon: String
    var label: String? = nil
    var tint: Color = .primary
    var background: Color = Color.white.opacity(0.12)
    let action: () -> Void

    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))

                if let label {
                    Text(label)
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.trailing, 2)
                }
            }
            .foregroundColor(tint.opacity(isHovering ? 1.0 : 0.85))
            .padding(.horizontal, label == nil ? 10 : 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(background.opacity(isHovering ? 1.0 : 0.8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Color.white.opacity(0.18), lineWidth: 0.6)
                    )
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
