//
//  DownloadQueueView.swift
//  MagnetarStudio (macOS)
//
//  Floating panel showing active HuggingFace model downloads with pause/resume/cancel controls
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DownloadQueueView")

struct DownloadQueueView: View {
    @Binding var downloads: [String: DownloadProgress]
    let onPause: (String) -> Void
    let onResume: (String) -> Void
    let onCancel: (String) -> Void

    @State private var isHovered = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Download list
            if sortedDownloads.isEmpty {
                emptyState
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(sortedDownloads, id: \.jobId) { download in
                            DownloadQueueItem(
                                download: download,
                                onPause: { onPause(download.jobId) },
                                onResume: { onResume(download.jobId) },
                                onCancel: { onCancel(download.jobId) }
                            )
                            Divider()
                        }
                    }
                }
            }
        }
        .frame(width: 320, height: min(CGFloat(sortedDownloads.count * 80 + 52), 400))
        .background(.ultraThinMaterial)
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.2), radius: 10, y: 5)
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Image(systemName: "arrow.down.circle")
                .foregroundStyle(.orange)
            Text("Downloads")
                .font(.headline)

            Spacer()

            Text("\(activeCount) active")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "arrow.down.circle.dotted")
                .font(.system(size: 32))
                .foregroundStyle(.secondary)
            Text("No active downloads")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
    }

    // MARK: - Computed Properties

    private var sortedDownloads: [DownloadProgress] {
        downloads.values.sorted { a, b in
            // Active downloads first, then by progress
            if a.status == "downloading" && b.status != "downloading" {
                return true
            }
            if a.status != "downloading" && b.status == "downloading" {
                return false
            }
            return a.progress > b.progress
        }
    }

    private var activeCount: Int {
        downloads.values.filter { $0.status == "downloading" }.count
    }
}

// MARK: - Download Queue Item

struct DownloadQueueItem: View {
    let download: DownloadProgress
    let onPause: () -> Void
    let onResume: () -> Void
    let onCancel: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Model icon
            Image(systemName: "face.smiling.fill")
                .font(.title3)
                .foregroundStyle(
                    LinearGradient(colors: [.yellow, .orange], startPoint: .topLeading, endPoint: .bottomTrailing)
                )

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(modelName)
                    .font(.caption)
                    .fontWeight(.medium)
                    .lineLimit(1)

                // Progress bar
                ProgressView(value: download.progress / 100)
                    .tint(statusColor)

                // Status row
                HStack(spacing: 8) {
                    Text(statusText)
                        .font(.caption2)
                        .foregroundStyle(statusColor)

                    if download.status == "downloading" {
                        Text("•")
                            .foregroundStyle(.secondary)
                        Text(download.speedFormatted)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Text("•")
                            .foregroundStyle(.secondary)
                        Text(download.etaFormatted)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()
                }
            }

            // Action buttons
            HStack(spacing: 4) {
                if download.status == "downloading" {
                    Button(action: onPause) {
                        Image(systemName: "pause.fill")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                    .help("Pause download")
                } else if download.status == "paused" {
                    Button(action: onResume) {
                        Image(systemName: "play.fill")
                            .font(.caption)
                            .foregroundStyle(.green)
                    }
                    .buttonStyle(.plain)
                    .help("Resume download")
                }

                Button(action: onCancel) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(.red.opacity(0.7))
                }
                .buttonStyle(.plain)
                .help("Cancel download")
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(isHovered ? Color.surfaceTertiary.opacity(0.3) : Color.clear)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }

    // MARK: - Computed Properties

    private var modelName: String {
        download.modelId ?? "Unknown Model"
    }

    private var statusText: String {
        switch download.status {
        case "starting": return "Starting..."
        case "downloading": return "\(Int(download.progress))%"
        case "verifying": return "Verifying..."
        case "paused": return "Paused"
        case "failed": return download.error ?? "Failed"
        case "canceled": return "Canceled"
        case "completed": return "Complete"
        default: return download.status.capitalized
        }
    }

    private var statusColor: Color {
        switch download.status {
        case "downloading": return .orange
        case "paused": return .yellow
        case "verifying": return .blue
        case "completed": return .green
        case "failed", "canceled": return .red
        default: return .secondary
        }
    }
}

// MARK: - Download Queue Manager

@MainActor
@Observable
class DownloadQueueManager {
    var downloads: [String: DownloadProgress] = [:]
    var showQueue = false

    private let huggingFaceService = HuggingFaceService.shared

    var hasActiveDownloads: Bool {
        downloads.values.contains { $0.status == "downloading" }
    }

    var activeCount: Int {
        downloads.values.filter { $0.status == "downloading" }.count
    }

    func pauseDownload(jobId: String) {
        // API call would go here
        logger.info("Pause requested for job: \(jobId)")
        // For now, just update local state (backend support needed)
        if downloads[jobId] != nil {
            // Would need mutable DownloadProgress or a wrapper
            logger.info("Pause not yet implemented in backend")
        }
    }

    func resumeDownload(jobId: String) {
        logger.info("Resume requested for job: \(jobId)")
        // Backend support needed
    }

    func cancelDownload(jobId: String) {
        logger.info("Cancel requested for job: \(jobId)")
        downloads.removeValue(forKey: jobId)
        // Backend cancel call would go here
    }
}

// MARK: - Download Queue Button (for toolbar)

struct DownloadQueueButton: View {
    @Binding var downloads: [String: DownloadProgress]
    @Binding var showQueue: Bool

    @State private var isHovered = false

    var body: some View {
        Button {
            showQueue.toggle()
        } label: {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "arrow.down.circle")
                    .font(.body)
                    .foregroundStyle(hasActiveDownloads ? .orange : .secondary)

                // Badge for active count
                if activeCount > 0 {
                    Text("\(activeCount)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(3)
                        .background(Circle().fill(Color.orange))
                        .offset(x: 6, y: -6)
                }
            }
            .frame(width: 28, height: 28)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isHovered ? Color.surfaceTertiary : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .help("Download queue")
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
        .popover(isPresented: $showQueue, arrowEdge: .bottom) {
            DownloadQueueView(
                downloads: $downloads,
                onPause: { _ in },
                onResume: { _ in },
                onCancel: { jobId in
                    downloads.removeValue(forKey: jobId)
                }
            )
        }
    }

    private var hasActiveDownloads: Bool {
        downloads.values.contains { $0.status == "downloading" }
    }

    private var activeCount: Int {
        downloads.values.filter { $0.status == "downloading" }.count
    }
}

// MARK: - Preview

#Preview {
    VStack {
        DownloadQueueView(
            downloads: .constant([
                "job1": DownloadProgress(
                    jobId: "job1",
                    status: "downloading",
                    progress: 45,
                    downloadedBytes: 2_000_000_000,
                    totalBytes: 4_500_000_000,
                    speedBps: 50_000_000,
                    etaSeconds: 120,
                    message: "Downloading...",
                    modelId: "mistral-7b-instruct",
                    error: nil
                ),
                "job2": DownloadProgress(
                    jobId: "job2",
                    status: "paused",
                    progress: 30,
                    downloadedBytes: 1_200_000_000,
                    totalBytes: 4_000_000_000,
                    speedBps: 0,
                    etaSeconds: nil,
                    message: "Paused",
                    modelId: "codellama-13b",
                    error: nil
                )
            ]),
            onPause: { _ in },
            onResume: { _ in },
            onCancel: { _ in }
        )
    }
    .padding(40)
    .background(Color.surfacePrimary)
}
