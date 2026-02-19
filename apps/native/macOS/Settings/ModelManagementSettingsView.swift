//
//  ModelManagementSettingsView.swift
//  MedStation
//
//  Settings panel for MLX model status and configuration.
//

import SwiftUI

struct ModelManagementSettingsView: View {
    @State private var engine = MLXInferenceEngine.shared

    var body: some View {
        Form {
            Section("MedGemma Model") {
                modelStatusRow
                modelInfoRow("Model ID", "mlx-community/medgemma-4b-it-4bit")
                modelInfoRow("Architecture", "Gemma 3 (VLM) — 4-bit quantized")
                modelInfoRow("Parameters", "4 billion")
                modelInfoRow("Approx. Size", "~3 GB")
                modelInfoRow("Inference", "MLX Swift on Apple Silicon (Metal)")
            }

            Section("Safety") {
                modelInfoRow("Safety Guard", "9-category post-processing validation")
                modelInfoRow("Model Gate", "Only approved medical models allowed")
                modelInfoRow("Privacy", "100% on-device — no patient data leaves this Mac")
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    @ViewBuilder
    private var modelStatusRow: some View {
        HStack {
            Text("Status")
                .foregroundStyle(.secondary)
            Spacer()
            switch engine.status {
            case .idle:
                Label("Not Loaded", systemImage: "circle")
                    .foregroundStyle(.secondary)
            case .downloading(let progress):
                HStack(spacing: 6) {
                    ProgressView(value: progress)
                        .frame(width: 80)
                    Text("\(Int(progress * 100))%")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loading:
                HStack(spacing: 6) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Loading...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .ready:
                Label("Ready", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
            case .failed(let message):
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .font(.caption)
            }
        }
    }

    private func modelInfoRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.callout)
        }
    }
}
