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
    @State private var showActivity = false
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
                ControlCluster(
                    terminalCount: terminalCount,
                    showTerminals: $showTerminals,
                    showActivity: $showActivity,
                    showPanicMode: $showPanicMode
                )

                Spacer()

                BrandCluster()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .sheet(isPresented: $showActivity) {
                ActivitySheet()
            }
            .sheet(isPresented: $showPanicMode) {
                PanicModeSheet()
            }
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
    @Binding var showActivity: Bool
    @Binding var showPanicMode: Bool

    var body: some View {
        HStack(spacing: 10) {
            HeaderToolbarButton(icon: "terminal", label: "\(terminalCount)") {
                openSystemTerminal()
            }
            .help("Open Terminal")

            HeaderToolbarButton(icon: "chart.bar.fill") {
                showActivity = true
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

    private func openSystemTerminal() {
        // Try to open iTerm2 first, then fall back to Terminal.app
        let iTerm = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.googlecode.iterm2")
        let terminal = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.Terminal")

        if let iTermURL = iTerm {
            NSWorkspace.shared.open(iTermURL)
        } else if let terminalURL = terminal {
            NSWorkspace.shared.open(terminalURL)
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

// MARK: - Sheet Views

private struct ActivitySheet: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Activity Monitor")
                .font(.system(size: 18, weight: .bold))

            Text("Activity monitoring coming soon")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

private struct PanicModeSheet: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundColor(.red)

            Text("Panic Mode")
                .font(.system(size: 18, weight: .bold))

            Text("Emergency shutdown and security features coming soon")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
