//
//  OrchestratorInitializer.swift
//  MagnetarStudio
//
//  Initializes and registers orchestrators on app startup
//  Part of Noah's Ark for the Digital Age - Intelligent routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "OrchestratorInitializer")

/// Initializes orchestrators and registers them with OrchestratorManager
@MainActor
class OrchestratorInitializer {
    static func initialize() async {
        let manager = OrchestratorManager.shared

        // Register Apple FM Orchestrator (primary)
        let appleFM = AppleFMOrchestrator()
        manager.register(appleFM)

        // Register Mock Orchestrator (fallback)
        let mock = MockOrchestrator()
        manager.register(mock)

        // Check health
        let health = await manager.healthCheck()
        logger.info("Orchestrator Health - Available: \(health.available.joined(separator: ", ")), Unavailable: \(health.unavailable.joined(separator: ", ")), Active: \(health.activeOrchestrator ?? "None")")

        // Get active orchestrator
        if let active = await manager.getActiveOrchestrator() {
            logger.info("Active orchestrator: \(active.displayName)")
        } else {
            logger.error("No orchestrator available!")
        }
    }
}
