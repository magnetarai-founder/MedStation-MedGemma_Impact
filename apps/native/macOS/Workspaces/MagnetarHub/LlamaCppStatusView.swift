//
//  LlamaCppStatusView.swift
//  MagnetarStudio (macOS)
//
//  llama.cpp server status with controls - mirrors HubOllamaStatus.swift
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "LlamaCppStatusView")

struct LlamaCppStatusView: View {
    @State private var status: LlamaCppStatus?
    @State private var isActionInProgress = false
    @State private var isHovered = false

    private let llamaCppService = LlamaCppService.shared
    private let refreshTimer = Timer.publish(every: 5, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(spacing: 8) {
            // Status indicator with pulse animation when running
            Circle()
                .fill(isRunning ? Color.green : Color.gray)
                .frame(width: 8, height: 8)
                .overlay(
                    Circle()
                        .stroke(isRunning ? Color.green.opacity(0.5) : Color.clear, lineWidth: 2)
                        .scaleEffect(isRunning ? 1.5 : 1.0)
                        .opacity(isRunning ? 0 : 1)
                        .animation(isRunning ? .easeOut(duration: 1.5).repeatForever(autoreverses: false) : .default, value: isRunning)
                )

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text("llama.cpp")
                        .font(.caption)
                        .fontWeight(.medium)
                    if isRunning, let port = status?.port {
                        Text(":\(port)")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }

                if let model = status?.modelLoaded {
                    Text(formatModelName(model))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                } else {
                    Text(isRunning ? "Ready" : "Stopped")
                        .font(.caption2)
                        .foregroundColor(isRunning ? .green : .secondary)
                }
            }

            Spacer()

            // Control buttons
            HStack(spacing: 4) {
                // Stop button (only when running)
                if isRunning {
                    StatusActionButton(
                        icon: "stop.fill",
                        color: .red,
                        help: "Stop llama.cpp",
                        disabled: isActionInProgress,
                        action: stop
                    )
                }

                // Restart button (only when running)
                if isRunning {
                    StatusActionButton(
                        icon: "arrow.clockwise",
                        color: .magnetarPrimary,
                        help: "Restart llama.cpp",
                        disabled: isActionInProgress,
                        isAnimating: isActionInProgress,
                        action: restart
                    )
                }

                // Health indicator
                if isRunning {
                    Circle()
                        .fill(status?.healthOk == true ? Color.green : Color.orange)
                        .frame(width: 6, height: 6)
                        .help(status?.healthOk == true ? "Healthy" : "Health check failed")
                }

                if isActionInProgress {
                    ProgressView()
                        .scaleEffect(0.6)
                        .frame(width: 12, height: 12)
                }
            }
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color.surfaceTertiary.opacity(0.5) : Color.surfaceTertiary.opacity(0.3))
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .task {
            await refreshStatus()
        }
        .onReceive(refreshTimer) { _ in
            Task { await refreshStatus() }
        }
    }

    // MARK: - Computed Properties

    private var isRunning: Bool {
        status?.running == true
    }

    // MARK: - Actions

    private func refreshStatus() async {
        do {
            status = try await llamaCppService.getStatus()
        } catch {
            // Server might not be running, that's ok
            status = nil
        }
    }

    private func stop() {
        isActionInProgress = true
        Task {
            do {
                status = try await llamaCppService.stopServer()
                logger.info("llama.cpp stopped")
            } catch {
                logger.error("Failed to stop llama.cpp: \(error.localizedDescription)")
            }
            isActionInProgress = false
        }
    }

    private func restart() {
        isActionInProgress = true
        Task {
            do {
                status = try await llamaCppService.restartServer()
                logger.info("llama.cpp restarted")
            } catch {
                logger.error("Failed to restart llama.cpp: \(error.localizedDescription)")
            }
            isActionInProgress = false
        }
    }

    // MARK: - Helpers

    private func formatModelName(_ path: String) -> String {
        // Extract just the filename without extension and path
        let filename = (path as NSString).lastPathComponent
        // Remove .gguf extension
        let name = filename.replacingOccurrences(of: ".gguf", with: "")
        // Truncate if too long
        if name.count > 20 {
            return String(name.prefix(18)) + "..."
        }
        return name
    }
}

// MARK: - Compact Status (for inline use)

struct LlamaCppStatusCompact: View {
    let status: LlamaCppStatus?

    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(status?.running == true ? Color.green : Color.gray)
                .frame(width: 6, height: 6)

            if let model = status?.modelLoaded {
                Text(formatModelName(model))
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            } else {
                Text("llama.cpp")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
    }

    private func formatModelName(_ path: String) -> String {
        let filename = (path as NSString).lastPathComponent
        let name = filename.replacingOccurrences(of: ".gguf", with: "")
        if name.count > 15 {
            return String(name.prefix(13)) + "..."
        }
        return name
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 20) {
        // Stopped state
        LlamaCppStatusView()

        // The view manages its own state, so we can't easily preview different states
        // In the actual app, it will fetch status from the service
    }
    .padding()
    .frame(width: 250)
    .background(Color.surfacePrimary)
}
