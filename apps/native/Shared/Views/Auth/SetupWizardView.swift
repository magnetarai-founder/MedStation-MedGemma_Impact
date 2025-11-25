//
//  SetupWizardView.swift
//  MagnetarStudio
//
//  Setup wizard shown when authState == .setupNeeded
//

import SwiftUI

struct SetupWizardView: View {
    @EnvironmentObject private var authStore: AuthStore

    @State private var currentStep = 0
    @State private var displayName: String = ""
    @State private var teamName: String = ""
    @State private var preferences: [String: Bool] = [:]

    private let totalSteps = 3

    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .ignoresSafeArea()

            LiquidGlassPanel(material: .thick) {
                VStack(spacing: 32) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "sparkles")
                            .font(.system(size: 48))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("Welcome to MagnetarStudio")
                            .font(.title)
                            .fontWeight(.bold)

                        Text("Let's get you set up")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    // Progress indicator
                    HStack(spacing: 8) {
                        ForEach(0..<totalSteps, id: \.self) { step in
                            Capsule()
                                .fill(step <= currentStep ? Color.blue : Color.gray.opacity(0.3))
                                .frame(height: 4)
                        }
                    }
                    .padding(.horizontal, 40)

                    // Step content
                    stepContent
                        .frame(height: 200)
                        .padding(.horizontal, 40)

                    // Navigation buttons
                    HStack(spacing: 16) {
                        if currentStep > 0 {
                            GlassButton("Back", icon: "chevron.left", style: .secondary) {
                                withAnimation {
                                    currentStep -= 1
                                }
                            }
                        }

                        Spacer()

                        if currentStep < totalSteps - 1 {
                            GlassButton("Next", icon: "chevron.right", style: .primary) {
                                withAnimation {
                                    currentStep += 1
                                }
                            }
                            .disabled(!canProceed)
                        } else {
                            GlassButton("Complete Setup", icon: "checkmark", style: .primary) {
                                Task {
                                    await completeSetup()
                                }
                            }
                            .disabled(authStore.loading)
                        }
                    }
                    .padding(.horizontal, 40)
                }
                .padding(40)
            }
            .frame(width: 600, height: 500)
        }
    }

    // MARK: - Step Content

    @ViewBuilder
    private var stepContent: some View {
        switch currentStep {
        case 0:
            VStack(spacing: 16) {
                Text("What should we call you?")
                    .font(.headline)

                TextField("Display Name", text: $displayName)
                    .textFieldStyle(.roundedBorder)
                    .frame(maxWidth: 400)

                Text("You can change this later in settings")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

        case 1:
            VStack(spacing: 16) {
                Text("Create or join a team")
                    .font(.headline)

                TextField("Team Name (optional)", text: $teamName)
                    .textFieldStyle(.roundedBorder)
                    .frame(maxWidth: 400)

                Text("Teams allow you to collaborate with others")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

        case 2:
            VStack(spacing: 16) {
                Text("Choose your preferences")
                    .font(.headline)

                VStack(alignment: .leading, spacing: 12) {
                    Toggle("Enable notifications", isOn: Binding(
                        get: { preferences["notifications"] ?? true },
                        set: { preferences["notifications"] = $0 }
                    ))

                    Toggle("Enable analytics", isOn: Binding(
                        get: { preferences["analytics"] ?? false },
                        set: { preferences["analytics"] = $0 }
                    ))

                    Toggle("Start with database workspace", isOn: Binding(
                        get: { preferences["defaultDatabase"] ?? true },
                        set: { preferences["defaultDatabase"] = $0 }
                    ))
                }
                .frame(maxWidth: 400)
            }

        default:
            EmptyView()
        }
    }

    // MARK: - Validation

    private var canProceed: Bool {
        switch currentStep {
        case 0:
            return !displayName.isEmpty
        case 1:
            return true // Team name is optional
        case 2:
            return true // Preferences are optional
        default:
            return false
        }
    }

    // MARK: - Complete Setup

    private func completeSetup() async {
        do {
            // Build request to mark setup as complete
            let url = URL(string: "http://localhost:8000/api/v1/setup/complete")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            // Send setup data (displayName, teamName, preferences)
            let requestBody: [String: Any] = [
                "displayName": displayName,
                "teamName": teamName,
                "preferences": preferences
            ]
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

            // Make request
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                print("Setup wizard: Invalid response")
                authStore.completeSetup()  // Complete locally even if backend fails
                return
            }

            if httpResponse.statusCode == 200 {
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    print("Setup wizard complete: \(json["message"] ?? "Success")")
                }
            } else {
                print("Setup wizard: Server returned status \(httpResponse.statusCode)")
            }

            // Complete setup locally
            authStore.completeSetup()

        } catch {
            print("Setup wizard error: \(error)")
            // Complete locally even if backend call fails
            authStore.completeSetup()
        }
    }
}

// MARK: - Preview

#Preview {
    SetupWizardView()
        .environmentObject(AuthStore.shared)
        .frame(width: 1200, height: 800)
}
