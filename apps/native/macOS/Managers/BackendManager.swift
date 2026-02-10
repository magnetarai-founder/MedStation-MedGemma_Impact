//
//  BackendManager.swift
//  MedStation (macOS)
//
//  Backend server management - Extracted from MedStationApp.swift (Phase 6.15)
//  Handles auto-start, health monitoring, and process lifecycle
//

import Foundation
import AppKit
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "BackendManager")

@MainActor
final class BackendManager {
    static let shared = BackendManager()

    private var backendProcess: Process?
    private var logFileHandle: FileHandle?
    private var isStarting = false // Prevent concurrent starts

    private init() {}

    // MARK: - Auto-start

    func autoStartBackend() async {
        // Prevent concurrent start attempts
        if isStarting {
            logger.info("Backend startup already in progress, skipping duplicate request")
            return
        }

        logger.info("Checking backend server status...")

        // Check if backend is already running
        let isRunning = await checkBackendHealth()

        if isRunning {
            logger.info("Backend server already running")
            return
        }

        // Check if we have a process reference and it's still running
        if let process = backendProcess, process.isRunning {
            logger.info("Backend process already running (PID: \(process.processIdentifier))")
            return
        }

        // Set flag to prevent concurrent starts
        isStarting = true
        defer { isStarting = false }

        logger.info("Starting MedStation backend server...")

        // Get project root directory
        logger.debug("Looking for project root...")
        guard let projectRoot = findProjectRoot() else {
            logger.error("Could not find project root directory")
            logger.error("Bundle path: \(Bundle.main.bundleURL.path)")
            logger.critical("Backend will NOT start automatically!")
            logger.info("Please start backend manually: cd apps/backend && python -m uvicorn api.main:app")
            return
        }

        logger.info("Found project root: \(projectRoot.path)")

        // Start backend server in background
        let venvPython = projectRoot.appendingPathComponent("venv/bin/python")
        let backendPath = projectRoot.appendingPathComponent("apps/backend")

        logger.debug("Checking python: \(venvPython.path)")
        guard FileManager.default.fileExists(atPath: venvPython.path) else {
            logger.error("Python venv not found: \(venvPython.path)")
            logger.critical("Backend will NOT start automatically!")
            return
        }

        logger.debug("Checking backend: \(backendPath.path)")
        guard FileManager.default.fileExists(atPath: backendPath.path) else {
            logger.error("Backend directory not found: \(backendPath.path)")
            logger.critical("Backend will NOT start automatically!")
            return
        }

        let task = Process()
        task.executableURL = venvPython
        task.arguments = ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
        task.currentDirectoryURL = backendPath

        // CRITICAL: Set environment variables for backend
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"
        environment["MEDSTATION_ENV"] = "development"
        // Add packages/ to PYTHONPATH so neutron_core is importable
        let packagesPath = projectRoot.appendingPathComponent("packages").path
        if let existing = environment["PYTHONPATH"] {
            environment["PYTHONPATH"] = "\(packagesPath):\(existing)"
        } else {
            environment["PYTHONPATH"] = packagesPath
        }
        task.environment = environment

        logger.info("All paths verified")
        logger.debug("Python: \(venvPython.path)")
        logger.debug("Working dir: \(backendPath.path)")
        logger.info("Starting uvicorn...")

        // Redirect output to a log file for debugging
        let logFile = FileManager.default.temporaryDirectory
            .appendingPathComponent("magnetar_backend.log")
        FileManager.default.createFile(atPath: logFile.path, contents: nil)

        // Close any previous log handle before opening a new one
        try? logFileHandle?.close()
        logFileHandle = nil

        if let logHandle = FileHandle(forWritingAtPath: logFile.path) {
            self.logFileHandle = logHandle
            task.standardOutput = logHandle
            task.standardError = logHandle
            logger.debug("Backend logs: \(logFile.path)")
        }

        do {
            try task.run()

            // Keep process reference alive
            self.backendProcess = task

            logger.info("Backend server started successfully (PID: \(task.processIdentifier))")

            // Wait for server to initialize with retries
            var attempts = 0
            var healthy = false

            while attempts < 10 && !healthy {
                try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
                healthy = await checkBackendHealth()
                attempts += 1

                if !healthy {
                    logger.debug("Waiting for backend... (attempt \(attempts)/10)")
                }
            }

            if healthy {
                logger.info("Backend server is healthy and responding")
            } else {
                logger.warning("Backend server started but not responding after 10 seconds")
                logger.warning("Check logs at: \(logFile.path)")
            }
        } catch {
            logger.critical("Failed to start backend server: \(error)")
            logger.error("Error details: \(error.localizedDescription)")

            // Show alert to user - Already on @MainActor, no dispatch needed
            let alert = NSAlert()
            alert.messageText = "Backend Server Failed to Start"
            alert.informativeText = "MedStation requires the backend server to function. Please check the console logs for details."
            alert.alertStyle = .critical
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }

    // MARK: - Health Monitoring

    func monitorBackendHealth() async {
        // Monitor backend health every 30 seconds and restart if needed
        var consecutiveFailures = 0

        while true {
            try? await Task.sleep(nanoseconds: 30_000_000_000) // 30 seconds

            let isHealthy = await checkBackendHealth()

            if !isHealthy {
                consecutiveFailures += 1

                // Only restart after 3 consecutive failures (90 seconds)
                // This prevents aggressive restarts during temporary issues
                if consecutiveFailures >= 3 {
                    logger.warning("Backend health check failed 3 times - attempting restart...")
                    await autoStartBackend()
                    consecutiveFailures = 0 // Reset counter after restart attempt
                } else {
                    logger.debug("Backend health check failed (\(consecutiveFailures)/3)")
                }
            } else {
                // Reset failure counter on successful health check
                consecutiveFailures = 0
            }
        }
    }

    func checkBackendHealth() async -> Bool {
        guard let url = URL(string: APIConfiguration.shared.healthURL) else { return false }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            if let httpResponse = response as? HTTPURLResponse {
                return httpResponse.statusCode == 200
            }
        } catch {
            // Server not responding
        }

        return false
    }

    // MARK: - Shutdown

    func terminateBackend() {
        if let process = backendProcess, process.isRunning {
            logger.info("Stopping backend server...")
            process.terminate()
            backendProcess = nil
        }
        try? logFileHandle?.close()
        logFileHandle = nil
    }

    // MARK: - Project Root Finding

    private func findProjectRoot() -> URL? {
        // CRITICAL: This must ALWAYS find the project root for backend auto-start

        // Method 1: Walk up from bundle (works in both dev and production)
        var current = Bundle.main.bundleURL

        for _ in 0..<15 {
            let venvPython = current.appendingPathComponent("venv/bin/python")
            let backendPath = current.appendingPathComponent("apps/backend")

            if FileManager.default.fileExists(atPath: venvPython.path) &&
               FileManager.default.fileExists(atPath: backendPath.path) {
                return current
            }

            current = current.deletingLastPathComponent()
        }

        // Method 2: Check common locations
        let commonPaths = [
            NSHomeDirectory() + "/Documents/MedStation",
            "/Applications/MedStation.app/Contents/Resources"
        ]

        for path in commonPaths {
            let url = URL(fileURLWithPath: path)
            let venvPython = url.appendingPathComponent("venv/bin/python")
            let backendPath = url.appendingPathComponent("apps/backend")

            if FileManager.default.fileExists(atPath: venvPython.path) &&
               FileManager.default.fileExists(atPath: backendPath.path) {
                return url
            }
        }

        return nil
    }
}
