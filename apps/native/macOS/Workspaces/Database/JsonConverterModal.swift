//
//  JsonConverterModal.swift
//  MagnetarStudio (macOS)
//
//  JSON to Excel converter modal - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI

struct JsonConverterModal: View {
    @Binding var isPresented: Bool
    var databaseStore: DatabaseStore

    @State private var jsonInput: String = ""
    @State private var isConverting: Bool = false
    @State private var errorMessage: String? = nil
    @State private var successMessage: String? = nil

    var body: some View {
        StructuredModal(title: "JSON to Excel Converter", isPresented: $isPresented) {
            VStack(spacing: 20) {
                // Instructions
                VStack(alignment: .leading, spacing: 8) {
                    Text("Paste your JSON data below to convert it to Excel format")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Text("The JSON should be an array of objects with consistent keys")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                // JSON Input
                VStack(alignment: .leading, spacing: 8) {
                    Text("JSON Data")
                        .font(.system(size: 13, weight: .medium))

                    TextEditor(text: $jsonInput)
                        .font(.system(size: 12, design: .monospaced))
                        .frame(height: 300)
                        .overlay(
                            RoundedRectangle(cornerRadius: 4)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }

                // Status Messages
                if let error = errorMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }

                if let success = successMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text(success)
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }

                // Convert Button
                Button {
                    Task { await convertJson() }
                } label: {
                    HStack {
                        if isConverting {
                            ProgressView()
                                .scaleEffect(0.8)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: "arrow.right.doc.on.clipboard")
                        }
                        Text(isConverting ? "Converting..." : "Convert to Excel")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(jsonInput.isEmpty || isConverting)
            }
            .padding(24)
        }
    }

    @MainActor
    private func convertJson() async {
        guard let sessionId = databaseStore.sessionId else {
            errorMessage = "No active session"
            return
        }

        isConverting = true
        errorMessage = nil
        successMessage = nil

        do {
            let response: JsonConvertResponse = try await ApiClient.shared.request(
                path: "/v1/sessions/\(sessionId)/json/convert",
                method: .post,
                jsonBody: ["json_data": jsonInput]
            )

            successMessage = "Converted successfully! File: \(response.filename)"
            isConverting = false

            // Auto-close after 2 seconds
            try? await Task.sleep(for: .seconds(2))
            isPresented = false
        } catch {
            errorMessage = error.localizedDescription
            isConverting = false
        }
    }
}
