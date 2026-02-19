//
//  BackendManager.swift
//  MedStation (macOS)
//
//  Stub — the Python backend has been replaced by native MLX inference.
//  This file is kept as a no-op so existing call sites compile without changes.
//  Will be fully removed once all references are cleaned up.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "BackendManager")

@MainActor
final class BackendManager {
    static let shared = BackendManager()
    private init() {}

    func autoStartBackend() async {
        logger.debug("Backend not needed — using MLX native inference")
    }

    func monitorBackendHealth() async {
        logger.debug("Health monitoring not needed — using MLX native inference")
    }

    func checkBackendHealth() async -> Bool { true }

    func terminateBackend() {}
}
