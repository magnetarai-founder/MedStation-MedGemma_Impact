//
//  ModelDownloadView.swift
//  MedStation (macOS)
//
//  First-launch UI for downloading the MedGemma MLX model (~3 GB).
//  Binds to MLXInferenceEngine.status to show progress.
//

import SwiftUI

struct ModelDownloadView: View {
    @State private var engine = MLXInferenceEngine.shared

    var body: some View {
        VStack(spacing: 16) {
            switch engine.status {
            case .idle:
                idleView
            case .downloading(let progress):
                downloadingView(progress: progress)
            case .loading:
                loadingView
            case .ready:
                readyView
            case .failed(let message):
                failedView(message: message)
            }
        }
        .frame(maxWidth: 400)
        .padding(32)
    }

    // MARK: - Status Views

    private var idleView: some View {
        VStack(spacing: 12) {
            Image(systemName: "brain")
                .font(.system(size: 40))
                .foregroundStyle(.secondary)
            Text("MedGemma Model Required")
                .font(.headline)
            Text("MedStation needs to download the MedGemma 4B model (~3 GB) for on-device medical inference.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Download Model") {
                Task { try? await engine.loadModel() }
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private func downloadingView(progress: Double) -> some View {
        VStack(spacing: 12) {
            ProgressView(value: progress) {
                Text("Downloading MedGemma")
                    .font(.headline)
            } currentValueLabel: {
                Text("\(Int(progress * 100))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .controlSize(.large)
            Text("Loading model into memory...")
                .font(.headline)
            Text("This may take 15–30 seconds depending on your Mac.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var readyView: some View {
        VStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 40))
                .foregroundStyle(.green)
            Text("MedGemma Ready")
                .font(.headline)
        }
    }

    private func failedView(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 40))
                .foregroundStyle(.orange)
            Text("Model Download Failed")
                .font(.headline)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") {
                Task { try? await engine.loadModel() }
            }
            .buttonStyle(.borderedProminent)
        }
    }
}
