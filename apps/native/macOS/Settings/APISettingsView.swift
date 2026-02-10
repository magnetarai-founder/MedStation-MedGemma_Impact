//
//  APISettingsView.swift
//  MedStation
//
//  Settings panel for API configuration.
//

import SwiftUI

// MARK: - API Settings

struct APISettingsView: View {
    @Binding var apiBaseURL: String
    @Binding var defaultModel: String

    let availableModels = ["mistral", "llama3", "qwen", "codestral"]
    @State private var connectionStatus: SimpleStatus = .idle

    var body: some View {
        Form {
            Section("Backend API") {
                TextField("API Base URL", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)

                Button("Test Connection") {
                    Task { await testConnection() }
                }
                statusLabel(connectionStatus)
            }

            Section("AI Models") {
                Picker("Default Model", selection: $defaultModel) {
                    ForEach(availableModels, id: \.self) { model in
                        Text(model.capitalized).tag(model)
                    }
                }

                Text("Default model for new chat sessions")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Actions

    private func testConnection() async {
        await MainActor.run { connectionStatus = .loading }

        let trimmedBase = apiBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let baseURL = URL(string: trimmedBase) else {
            await MainActor.run {
                connectionStatus = .failure("Invalid base URL")
            }
            return
        }

        let healthURL = baseURL.appendingPathComponent("health")
        var request = URLRequest(url: healthURL)
        request.httpMethod = "GET"
        request.timeoutInterval = 8

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                await MainActor.run {
                    connectionStatus = .failure("Invalid response")
                }
                return
            }

            if (200...299).contains(http.statusCode) {
                await MainActor.run {
                    connectionStatus = .success("Connected (\(http.statusCode))")
                }
            } else {
                await MainActor.run {
                    connectionStatus = .failure("Status \(http.statusCode)")
                }
            }
        } catch {
            await MainActor.run {
                connectionStatus = .failure(error.localizedDescription)
            }
        }
    }
}
