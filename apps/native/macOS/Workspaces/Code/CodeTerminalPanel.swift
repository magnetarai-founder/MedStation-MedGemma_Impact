//
//  CodeTerminalPanel.swift
//  MagnetarStudio (macOS)
//
//  Terminal panel with session tabs - Enhanced in Phase 2
//  Integrates with CodingStore for session management
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeTerminalPanel")

struct CodeTerminalPanel: View {
    @Binding var showTerminal: Bool
    @Bindable var codingStore: CodingStore
    let onSpawnTerminal: () async -> Void

    @State private var selectedSessionId: UUID?
    @State private var showingTerminalPicker = false
    @State private var capturedOutput: String = ""
    @State private var isCapturing = false

    var body: some View {
        VStack(spacing: 0) {
            // Terminal header with session tabs
            terminalHeader

            Divider()

            // Content area
            if codingStore.terminalSessions.isEmpty {
                emptyState
            } else {
                sessionContent
            }
        }
    }

    // MARK: - Header

    private var terminalHeader: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "terminal")
                    .font(.system(size: 12))
                    .foregroundColor(.magnetarPrimary)

                Text("Terminal")
                    .font(.system(size: 12, weight: .semibold))

                // Session count badge
                if !codingStore.terminalSessions.isEmpty {
                    Text("\(codingStore.terminalSessions.count)")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.magnetarPrimary)
                        .clipShape(Capsule())
                }

                Spacer()

                // Terminal app indicator
                Button {
                    showingTerminalPicker.toggle()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: codingStore.preferredTerminal.iconName)
                            .font(.system(size: 11))
                        Text(codingStore.preferredTerminal.displayName)
                            .font(.system(size: 10))
                    }
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.surfaceTertiary.opacity(0.5))
                    .cornerRadius(4)
                }
                .buttonStyle(.plain)
                .popover(isPresented: $showingTerminalPicker) {
                    terminalPickerPopover
                }

                // New terminal button
                Button {
                    Task {
                        await onSpawnTerminal()
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 12))
                        Text("New")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)

                Button {
                    showTerminal = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.3))

            // Session tabs
            if !codingStore.terminalSessions.isEmpty {
                sessionTabs
            }
        }
    }

    // MARK: - Session Tabs

    private var sessionTabs: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 2) {
                ForEach(codingStore.terminalSessions) { session in
                    TerminalSessionTab(
                        session: session,
                        isSelected: selectedSessionId == session.id || (selectedSessionId == nil && session.id == codingStore.terminalSessions.first?.id),
                        onSelect: {
                            selectedSessionId = session.id
                            codingStore.activeTerminalId = session.id
                        },
                        onClose: {
                            closeSession(session)
                        }
                    )
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
        }
        .background(Color.surfaceTertiary.opacity(0.2))
    }

    // MARK: - Terminal Picker Popover

    private var terminalPickerPopover: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Terminal App")
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(.secondary)
                .padding(.horizontal, 8)
                .padding(.top, 8)

            ForEach(TerminalApp.allCases, id: \.self) { app in
                Button {
                    codingStore.preferredTerminal = app
                    showingTerminalPicker = false
                } label: {
                    HStack {
                        Image(systemName: app.iconName)
                            .frame(width: 20)
                        Text(app.displayName)
                        Spacer()
                        if codingStore.preferredTerminal == app {
                            Image(systemName: "checkmark")
                                .foregroundColor(.magnetarPrimary)
                        }
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
        }
        .frame(width: 180)
        .padding(.vertical, 4)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 8) {
                    Image(systemName: "terminal.fill")
                        .font(.system(size: 24))
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("System Terminal Integration")
                            .font(.system(size: 13, weight: .semibold))

                        Text("Click 'New' to spawn a terminal window")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.bottom, 8)

                VStack(alignment: .leading, spacing: 8) {
                    CodeTerminalInfoRow(
                        icon: "checkmark.circle.fill",
                        text: "Opens \(codingStore.preferredTerminal.displayName)",
                        color: .green
                    )

                    CodeTerminalInfoRow(
                        icon: "checkmark.circle.fill",
                        text: "Automatically starts in your workspace directory",
                        color: .green
                    )

                    CodeTerminalInfoRow(
                        icon: "sparkles",
                        text: "AI can analyze errors and suggest fixes",
                        color: .purple
                    )

                    CodeTerminalInfoRow(
                        icon: "arrow.left.arrow.right",
                        text: "Copy terminal output to share context with AI",
                        color: .blue
                    )
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Color.surfaceTertiary.opacity(0.1))
    }

    // MARK: - Session Content

    private var sessionContent: some View {
        VStack(spacing: 0) {
            if let sessionId = selectedSessionId ?? codingStore.terminalSessions.first?.id,
               let session = codingStore.terminalSessions.first(where: { $0.id == sessionId }) {
                sessionDetailView(session)
            }
        }
        .background(Color.surfaceTertiary.opacity(0.1))
    }

    private func sessionDetailView(_ session: CodingTerminalSession) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Session info
            HStack(spacing: 12) {
                // Terminal app badge
                HStack(spacing: 4) {
                    Image(systemName: session.terminalApp.iconName)
                        .font(.system(size: 11))
                    Text(session.terminalApp.displayName)
                        .font(.system(size: 11, weight: .medium))
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.surfaceTertiary)
                .cornerRadius(4)

                // Status indicator
                HStack(spacing: 4) {
                    Circle()
                        .fill(session.isActive ? Color.green : Color.gray)
                        .frame(width: 6, height: 6)
                    Text(session.isActive ? "Active" : "Inactive")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }

                Spacer()

                // Actions
                HStack(spacing: 8) {
                    Button {
                        Task {
                            await focusSession(session)
                        }
                    } label: {
                        Label("Focus", systemImage: "arrow.up.forward.app")
                            .font(.system(size: 10))
                    }
                    .buttonStyle(.plain)

                    Button {
                        Task {
                            await captureSessionOutput(session)
                        }
                    } label: {
                        if isCapturing {
                            ProgressView()
                                .scaleEffect(0.6)
                        } else {
                            Label("Capture", systemImage: "doc.on.clipboard")
                                .font(.system(size: 10))
                        }
                    }
                    .buttonStyle(.plain)
                    .disabled(isCapturing)
                }
            }

            // Working directory
            HStack(spacing: 4) {
                Image(systemName: "folder")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                Text(session.workingDirectory)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }

            // Last command (if any)
            if let lastCommand = session.lastCommand {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Last Command")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.secondary)

                    HStack {
                        Text("$")
                            .foregroundColor(.green)
                        Text(lastCommand)
                            .lineLimit(2)
                    }
                    .font(.system(size: 11, design: .monospaced))
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.black.opacity(0.3))
                    .cornerRadius(4)
                }
            }

            // Captured output
            if !capturedOutput.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("Captured Output")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundColor(.secondary)

                        Spacer()

                        Button {
                            sendOutputToAI()
                        } label: {
                            Label("Send to AI", systemImage: "sparkles")
                                .font(.system(size: 10))
                                .foregroundColor(.purple)
                        }
                        .buttonStyle(.plain)

                        Button {
                            capturedOutput = ""
                        } label: {
                            Image(systemName: "xmark.circle")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                        .buttonStyle(.plain)
                    }

                    ScrollView {
                        Text(capturedOutput)
                            .font(.system(size: 10, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 100)
                    .padding(8)
                    .background(Color.black.opacity(0.3))
                    .cornerRadius(4)
                }
            }

            Spacer()
        }
        .padding(12)
    }

    // MARK: - Actions

    private func closeSession(_ session: CodingTerminalSession) {
        withAnimation {
            codingStore.terminalSessions.removeAll { $0.id == session.id }
            if selectedSessionId == session.id {
                selectedSessionId = codingStore.terminalSessions.first?.id
            }
        }
    }

    private func focusSession(_ session: CodingTerminalSession) async {
        do {
            try await TerminalBridgeService.shared.focusTerminal(session.terminalApp)
        } catch {
            logger.error("Failed to focus terminal: \(error)")
        }
    }

    private func captureSessionOutput(_ session: CodingTerminalSession) async {
        isCapturing = true
        defer { isCapturing = false }

        do {
            try await TerminalBridgeService.shared.requestOutputCapture(in: session.terminalApp)

            // Check clipboard after capture
            if let content = NSPasteboard.general.string(forType: .string) {
                await MainActor.run {
                    capturedOutput = content
                }
            }
        } catch {
            logger.error("Failed to capture output: \(error)")
        }
    }

    private func sendOutputToAI() {
        guard !capturedOutput.isEmpty else { return }

        // Create terminal context and send to AI assistant
        let context = TerminalContext(
            command: codingStore.terminalSessions.first(where: { $0.id == selectedSessionId })?.lastCommand ?? "Unknown",
            output: capturedOutput,
            exitCode: 0,
            workingDirectory: codingStore.workingDirectory ?? "~",
            timestamp: Date()
        )

        codingStore.recordTerminalContext(context)

        // Clear captured output after sending
        capturedOutput = ""
    }
}

// MARK: - Terminal Session Tab

struct TerminalSessionTab: View {
    let session: CodingTerminalSession
    let isSelected: Bool
    let onSelect: () -> Void
    let onClose: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 6) {
            // Status dot
            Circle()
                .fill(session.isActive ? Color.green : Color.gray)
                .frame(width: 6, height: 6)

            // Terminal icon
            Image(systemName: session.terminalApp.iconName)
                .font(.system(size: 10))

            // Session name
            Text(sessionName)
                .font(.system(size: 11))
                .lineLimit(1)

            // Close button
            if isHovered || isSelected {
                Button {
                    onClose()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 8, weight: .bold))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.2) : (isHovered ? Color.surfaceTertiary : Color.clear))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(isSelected ? Color.magnetarPrimary.opacity(0.5) : Color.clear, lineWidth: 1)
        )
        .contentShape(Rectangle())
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            isHovered = hovering
        }
    }

    private var sessionName: String {
        // Use last path component of working directory
        let path = session.workingDirectory
        if let lastComponent = path.split(separator: "/").last {
            return String(lastComponent)
        }
        return session.terminalApp.displayName
    }
}

// MARK: - Terminal Info Row

struct CodeTerminalInfoRow: View {
    let icon: String
    let text: String
    let color: Color

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundColor(color)
                .frame(width: 16)

            Text(text)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// MARK: - Preview

#Preview {
    CodeTerminalPanel(
        showTerminal: .constant(true),
        codingStore: CodingStore.shared,
        onSpawnTerminal: {}
    )
    .frame(width: 600, height: 300)
}
