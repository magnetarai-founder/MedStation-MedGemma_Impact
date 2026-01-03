//
//  EmergencyConfirmationModal.swift
//  MagnetarStudio
//
//  Emergency mode confirmation UI with "I UNDERSTAND" input and countdown
//  FOR PERSECUTION SCENARIOS - This is the nuclear option
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "EmergencyConfirmationModal")

struct EmergencyConfirmationModal: View {
    @Environment(\.dismiss) private var dismiss
    @State private var userInput: String = ""
    @State private var countdown: Int = 10
    @State private var isExecuting: Bool = false
    @State private var showSecondConfirmation: Bool = false
    @State private var keyHoldProgress: Double = 0.0

    let onConfirm: (EmergencyTriggerMethod) -> Void

    // Explicit internal initializer for SwiftUI preview access
    init(onConfirm: @escaping (EmergencyTriggerMethod) -> Void) {
        self.onConfirm = onConfirm
    }

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
        .onDisappear {
            // Clean up key monitoring when modal closes
            stopKeyMonitoring()
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
                logger.warning("Emergency wipe starting in \(i)...")
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }

            // Execute emergency mode
            onConfirm(method)
            dismiss()
        }
    }

    // MARK: - Key Monitoring Implementation

    @State private var keyMonitor: Any?
    @State private var holdProgressTimer: Timer?
    @State private var isHoldingKeyCombo: Bool = false

    /// Required hold duration in seconds
    private let requiredHoldDuration: Double = 5.0

    private func startKeyMonitoring() {
        // Monitor for key down/up events to detect Cmd+Shift+Delete combo
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp, .flagsChanged]) { [self] event in
            handleKeyEvent(event)
            return event
        }
        logger.info("Key monitoring started for Cmd+Shift+Delete combo")
    }

    private func handleKeyEvent(_ event: NSEvent) {
        // Check if Cmd+Shift are held
        let modifiers = event.modifierFlags
        let hasCmd = modifiers.contains(.command)
        let hasShift = modifiers.contains(.shift)
        let isDeletePressed = isDeleteKeyPressed()

        // Check if all three keys are held
        if hasCmd && hasShift && isDeletePressed {
            if !isHoldingKeyCombo {
                startHoldTimer()
            }
        } else {
            if isHoldingKeyCombo {
                cancelHoldTimer()
            }
        }
    }

    private func startHoldTimer() {
        guard !isHoldingKeyCombo else { return }

        isHoldingKeyCombo = true
        keyHoldProgress = 0.0

        // Timer to update progress every 100ms
        holdProgressTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [self] timer in
            // Update on main thread
            DispatchQueue.main.async {
                // Verify keys are still held
                let modifiers = NSEvent.modifierFlags
                let hasCmd = modifiers.contains(.command)
                let hasShift = modifiers.contains(.shift)
                let isDeletePressed = self.isDeleteKeyPressed()

                if hasCmd && hasShift && isDeletePressed {
                    self.keyHoldProgress += 0.1 / self.requiredHoldDuration

                    if self.keyHoldProgress >= 1.0 {
                        // Combo held long enough - trigger emergency
                        timer.invalidate()
                        self.holdProgressTimer = nil
                        self.triggerEmergencyViaKeyCombo()
                    }
                } else {
                    // Keys released - cancel
                    self.cancelHoldTimer()
                }
            }
        }

        logger.info("Hold timer started - hold for \(requiredHoldDuration) seconds")
    }

    private func cancelHoldTimer() {
        holdProgressTimer?.invalidate()
        holdProgressTimer = nil
        isHoldingKeyCombo = false

        // Animate progress back to zero
        withAnimation(.easeOut(duration: 0.3)) {
            keyHoldProgress = 0.0
        }

        logger.debug("Hold timer cancelled")
    }

    private func triggerEmergencyViaKeyCombo() {
        logger.warning("Key combo trigger activated!")
        // Skip first confirmation, go straight to second (user already held for 5 seconds)
        showSecondConfirmation = true
        // Auto-execute after a brief moment for visibility
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 500_000_000)
            executeEmergency(method: .keyCombo)
        }
    }

    private func isDeleteKeyPressed() -> Bool {
        // Check if Delete key (keyCode 51) is currently pressed
        let keyCode: CGKeyCode = 51
        return CGEventSource.keyState(.hidSystemState, key: keyCode)
    }

    private func stopKeyMonitoring() {
        // Clean up key monitor
        if let monitor = keyMonitor {
            NSEvent.removeMonitor(monitor)
            keyMonitor = nil
        }

        // Clean up timer
        holdProgressTimer?.invalidate()
        holdProgressTimer = nil
        isHoldingKeyCombo = false

        logger.info("Key monitoring stopped")
    }
}

// MARK: - Preview

#Preview {
    EmergencyConfirmationModal(onConfirm: { method in
        logger.warning("Emergency mode confirmed via: \(method.rawValue)")
    })
}
