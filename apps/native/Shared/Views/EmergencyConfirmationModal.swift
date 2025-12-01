//
//  EmergencyConfirmationModal.swift
//  MagnetarStudio
//
//  Emergency mode confirmation UI with "I UNDERSTAND" input and countdown
//  FOR PERSECUTION SCENARIOS - This is the nuclear option
//

import SwiftUI

struct EmergencyConfirmationModal: View {
    @Environment(\.dismiss) private var dismiss
    @State private var userInput: String = ""
    @State private var countdown: Int = 10
    @State private var isExecuting: Bool = false
    @State private var showSecondConfirmation: Bool = false
    @State private var keyHoldProgress: Double = 0.0

    let onConfirm: (EmergencyTriggerMethod) -> Void

    // Timer for countdown
    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack {
            // Background blur
            Color.black.opacity(0.7)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                if showSecondConfirmation {
                    secondConfirmationView
                } else {
                    primaryConfirmationView
                }
            }
            .frame(width: 600, height: 500)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(nsColor: .windowBackgroundColor))
                    .shadow(color: .red.opacity(0.5), radius: 30)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(Color.red, lineWidth: 3)
            )
        }
        .onReceive(timer) { _ in
            handleCountdown()
        }
        .onAppear {
            // Start monitoring for key combo (Cmd+Shift+Delete hold)
            startKeyMonitoring()
        }
    }

    // MARK: - Primary Confirmation View

    private var primaryConfirmationView: some View {
        VStack(spacing: 24) {
            // Header
            VStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.red)

                Text("⚠️ EMERGENCY MODE ⚠️")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(.red)

                Text("THIS IS IRREVERSIBLE")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.secondary)
            }
            .padding(.top, 40)

            Divider()
                .background(Color.red.opacity(0.3))

            // Warning message
            VStack(alignment: .leading, spacing: 12) {
                Text("This will PERMANENTLY DELETE:")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.primary)

                VStack(alignment: .leading, spacing: 8) {
                    EmergencyWarningRow(icon: "lock.fill", text: "All vault files (sensitive + unsensitive)")
                    EmergencyWarningRow(icon: "arrow.clockwise.circle.fill", text: "All backups and models")
                    EmergencyWarningRow(icon: "doc.fill", text: "All audit logs and data")
                    EmergencyWarningRow(icon: "externaldrive.fill", text: "All cache and temporary files")
                    EmergencyWarningRow(icon: "app.fill", text: "The entire application (uninstall)")
                }
                .padding(.leading, 8)

                Text("THERE IS NO RECOVERY. THIS IS FINAL.")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.red)
                    .padding(.top, 8)
            }
            .padding(.horizontal, 32)

            Divider()
                .background(Color.red.opacity(0.3))

            // Confirmation input
            VStack(spacing: 12) {
                Text("Type \"I UNDERSTAND\" to proceed:")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                TextField("", text: $userInput)
                    .textFieldStyle(.plain)
                    .font(.system(size: 16, weight: .medium, design: .monospaced))
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(nsColor: .textBackgroundColor))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(userInput == "I UNDERSTAND" ? Color.red : Color.gray.opacity(0.3), lineWidth: 2)
                            )
                    )
                    .frame(width: 300)
                    .disabled(isExecuting)
                    .onChange(of: userInput) { _, newValue in
                        if newValue == "I UNDERSTAND" {
                            // First confirmation met
                            showSecondConfirmation = true
                        }
                    }

                // Alternative: Key combo hint
                Text("Or: Hold Cmd+Shift+Delete for 5 seconds")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                if keyHoldProgress > 0 {
                    ProgressView(value: keyHoldProgress)
                        .progressViewStyle(.linear)
                        .tint(.red)
                        .frame(width: 300)
                }
            }
            .padding(.horizontal, 32)

            Spacer()

            // Countdown and cancel
            HStack {
                Text("Window closes in \(countdown) seconds")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                Spacer()

                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)
                .disabled(isExecuting)
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 24)
        }
    }

    // MARK: - Second Confirmation View

    private var secondConfirmationView: some View {
        VStack(spacing: 24) {
            // Header
            VStack(spacing: 12) {
                Image(systemName: "flame.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.red)
                    .symbolEffect(.pulse)

                Text("FINAL WARNING")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(.red)

                Text("Are you absolutely sure?")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.secondary)
            }
            .padding(.top, 60)

            Divider()
                .background(Color.red.opacity(0.3))

            // Final message
            VStack(spacing: 16) {
                Text("Once you proceed:")
                    .font(.system(size: 16, weight: .semibold))

                VStack(alignment: .leading, spacing: 8) {
                    Text("• All data will be wiped with 7-pass DoD overwrite")
                    Text("• MagnetarStudio will uninstall itself")
                    Text("• This Mac will show no trace of the app")
                    Text("• Recovery is IMPOSSIBLE")
                }
                .font(.system(size: 14))
                .foregroundColor(.secondary)

                Text("This action cannot be undone.")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.red)
                    .padding(.top, 8)
            }
            .padding(.horizontal, 32)

            Spacer()

            // Action buttons
            HStack(spacing: 16) {
                Button("Cancel - Go Back") {
                    showSecondConfirmation = false
                    userInput = ""
                }
                .buttonStyle(.bordered)
                .disabled(isExecuting)

                Button(isExecuting ? "Executing..." : "Proceed with Emergency Mode") {
                    executeEmergency(method: .textConfirmation)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
                .disabled(isExecuting)
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 32)
        }
    }

    // MARK: - Helper Views

    private struct EmergencyWarningRow: View {
        let icon: String
        let text: String

        var body: some View {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(.red)
                    .frame(width: 20)

                Text(text)
                    .font(.system(size: 13))
                    .foregroundColor(.primary)

                Spacer()
            }
        }
    }

    // MARK: - Actions

    private func handleCountdown() {
        guard countdown > 0 else {
            // Countdown expired - close window
            dismiss()
            return
        }

        countdown -= 1
    }

    private func executeEmergency(method: EmergencyTriggerMethod) {
        isExecuting = true

        // Show "last chance" countdown (3 seconds)
        Task { @MainActor in
            for i in (1...3).reversed() {
                print("⚠️ Emergency wipe starting in \(i)...")
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }

            // Execute emergency mode
            onConfirm(method)
            dismiss()
        }
    }

    private func startKeyMonitoring() {
        // TODO: Implement NSEvent monitoring for Cmd+Shift+Delete hold
        // Track hold duration and update keyHoldProgress
        // If held for 5 seconds, trigger executeEmergency(method: .keyCombo)
        print("⚠️ TODO: Key combo monitoring not implemented yet")
    }
}

// MARK: - Preview

#Preview {
    EmergencyConfirmationModal { method in
        print("Emergency mode confirmed via: \(method.rawValue)")
    }
}
