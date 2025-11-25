//
//  Header.swift
//  MagnetarStudio
//
//  Global header bar matching React Header.tsx specs
//  - Gradient background with blur
//  - Left: Star button + badge
//  - Center: "MagnetarStudio" title (absolutely centered)
//  - Right: Terminal button + control buttons
//

import SwiftUI

struct Header: View {
    @State private var showModelManagement = false
    @State private var showTerminals = false
    @State private var showPanicMode = false
    @State private var terminalCount = 0

    var body: some View {
        ZStack(alignment: .center) {
            // Background gradient with blur
            LinearGradient(
                colors: [
                    Color(red: 0.24, green: 0.51, blue: 0.98, opacity: 0.08), // blue-50/80
                    Color(red: 0.55, green: 0.27, blue: 0.93, opacity: 0.08), // purple-50/80
                    Color(red: 0.98, green: 0.44, blue: 0.72, opacity: 0.08)  // pink-50/80
                ],
                startPoint: .leading,
                endPoint: .trailing
            )
            .overlay(
                Color.white.opacity(0.01)
                    .background(.ultraThinMaterial)
            )
            .ignoresSafeArea(edges: .top)

            // Content HStack
            HStack(alignment: .center, spacing: 12) {
                // Left cluster: Star button + badge
                HStack(spacing: 12) {
                    Button {
                        showModelManagement = true
                    } label: {
                        Image(systemName: "star.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(LinearGradient.magnetarGradient)
                            .frame(width: 40, height: 40)
                            .background(
                                Circle()
                                    .fill(Color.white.opacity(0.3))
                            )
                    }
                    .buttonStyle(.plain)
                    .scaleEffect(1.0)
                    .help("Model Management")

                    // Context badge placeholder
                    Text("Local")
                        .font(.system(size: 10, weight: .medium))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(
                            Capsule()
                                .fill(Color.green.opacity(0.2))
                        )
                        .foregroundColor(.green)
                }

                Spacer()

                // Center: Title (absolutely centered)
                // This Spacer + HStack trick ensures absolute centering
                HStack {
                    Spacer()
                }

                Spacer()

                // Right cluster: Terminal + controls + panic
                HStack(spacing: 12) {
                    // Terminal button + counter
                    Button {
                        showTerminals = true
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "terminal")
                                .font(.system(size: 20))

                            Text("\(terminalCount)")
                                .font(.system(size: 11))
                                .frame(minWidth: 20)
                        }
                        .foregroundColor(.secondary)
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.white.opacity(0.3))
                        )
                    }
                    .buttonStyle(.plain)
                    .help("Terminals")

                    // Activity button
                    Button {
                        // Show activity
                    } label: {
                        Image(systemName: "chart.bar")
                            .font(.system(size: 20))
                            .foregroundColor(.secondary)
                            .padding(8)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.white.opacity(0.3))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Activity")

                    // Panic button
                    Button {
                        showPanicMode = true
                    } label: {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 20))
                            .foregroundColor(.red.opacity(0.8))
                            .padding(8)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.red.opacity(0.1))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Panic Mode")
                }
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 14)

            // Absolutely centered title (overlay)
            Text("MagnetarStudio")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.primary)
        }
        .frame(height: 60)
        .overlay(
            // Bottom border
            Rectangle()
                .fill(Color.white.opacity(0.2))
                .frame(height: 1),
            alignment: .bottom
        )
        .sheet(isPresented: $showModelManagement) {
            // Model management view
            Text("Model Management")
                .frame(width: 400, height: 600)
        }
    }
}

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
