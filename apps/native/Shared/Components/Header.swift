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
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "Header")

struct Header: View {
    @State private var showActivity = false
    @State private var showPanicMode = false
    @State private var showEmergencyMode = false
    @Environment(\.openWindow) private var openWindow

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

            // Content
            HStack(alignment: .center, spacing: 16) {
                ControlCluster(
                    showActivity: $showActivity,
                    showPanicMode: $showPanicMode,
                    showEmergencyMode: $showEmergencyMode
                )

                Spacer()

                BrandCluster()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .sheet(isPresented: $showActivity) {
                ControlCenterSheet()
            }
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
