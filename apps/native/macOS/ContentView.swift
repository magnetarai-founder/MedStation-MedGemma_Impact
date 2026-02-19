//
//  ContentView.swift
//  MedStation
//
//  Root view - handles authentication state and main app shell.
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ContentView")

struct ContentView: View {
    @Environment(AuthStore.self) private var authStore

    var body: some View {
        Group {
            switch authStore.authState {
            case .checking, .welcome, .setupNeeded:
                ProgressView("Loading...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)

            case .authenticated:
                MainAppView()
            }
        }
        .task {
            await authStore.bootstrap()
        }
        .environment(authStore)
    }
}

// MARK: - Main App View

struct MainAppView: View {
    @Environment(NavigationStore.self) private var navigationStore
    @Environment(AuthStore.self) private var authStore
    @AppStorage("autoLockEnabled") private var autoLockEnabled = false
    @AppStorage("autoLockTimeout") private var autoLockTimeout = 15

    var body: some View {
        VStack(spacing: 0) {
            // Main content: Medical workspace
            WorkspaceHub()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .task(id: autoLockEnabled) {
            guard autoLockEnabled, autoLockTimeout > 0 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(30))
                guard autoLockEnabled else { break }
                let mouseIdle = CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: .mouseMoved)
                let keyIdle = CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: .keyDown)
                let idleSeconds = min(mouseIdle, keyIdle)
                let timeoutSeconds = Double(autoLockTimeout) * 60
                if idleSeconds > timeoutSeconds {
                    logger.info("Auto-lock triggered after \(Int(idleSeconds))s system idle")
                    authStore.lock()
                    break
                }
            }
        }
    }
}

// MARK: - Preview

#Preview("Welcome") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
}

#Preview("Authenticated") {
    ContentView()
        .frame(width: 1200, height: 800)
        .environment(NavigationStore())
        .environment(ChatStore())
}
