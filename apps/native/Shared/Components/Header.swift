//
//  Header.swift
//  MagnetarStudio
//
//  Simplified header: [+] [Chat | Files] [Panic]
//  - Left: Quick action menu (+) for spawnable windows
//  - Center: Core workspace tabs
//  - Right: Panic button only (safety feature)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "Header")

struct Header: View {
    @State private var showPanicMode = false
    @State private var showEmergencyMode = false

    var body: some View {
        ZStack(alignment: .center) {
            // macOS Tahoe Liquid Glass Header - completely transparent with subtle chroma
            ZStack {
                // Muted gradient with faint chroma sweep
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
            }
            .headerGlass()  // Applies @AppStorage("glassOpacity") controlled material
            .ignoresSafeArea(edges: .top)

            // Content - Simplified: [Tab Switcher] centered, [+] on right
            HStack(alignment: .center, spacing: 16) {
                // Left: Just the + button for spawnable windows
                QuickActionButton()

                Spacer()

                // Center: Tab switcher for core workspaces
                WorkspaceTabs()

                Spacer()

                // Right: AI toggle + Panic
                HStack(spacing: 8) {
                    AIToggleButton()

                    PanicButton(
                        showPanicMode: $showPanicMode,
                        showEmergencyMode: $showEmergencyMode
                    )
                }
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .sheet(isPresented: $showPanicMode) {
                PanicModeSheet()
            }
            .sheet(isPresented: $showEmergencyMode) {
                EmergencyConfirmationModal { method in
                    Task {
                        await handleEmergencyMode(method: method)
                    }
                }
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

    // MARK: - Emergency Mode Handler

    private func handleEmergencyMode(method: EmergencyTriggerMethod) async {
        logger.critical("Emergency mode triggered via: \(method.rawValue)")

        do {
            let report = try await EmergencyModeService.shared.triggerEmergency(
                reason: "User-initiated emergency from macOS app",
                confirmationMethod: method
            )

            if report.simulated {
                logger.info("SIMULATION COMPLETE: Files identified: \(report.filesWiped), Duration: \(String(format: "%.2f", report.durationSeconds))s")
            } else {
                logger.warning("EMERGENCY MODE COMPLETE: Files wiped: \(report.filesWiped), Duration: \(String(format: "%.2f", report.durationSeconds))s")

                if !report.errors.isEmpty {
                    logger.warning("Errors: \(report.errors.joined(separator: ", "))")
                }

                // App will terminate after self-uninstall
            }
        } catch {
            logger.error("Emergency mode error: \(error.localizedDescription)")
        }
    }
}

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
