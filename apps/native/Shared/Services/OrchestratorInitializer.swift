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
        print("📊 Orchestrator Health:")
        print("  Available: \(health.available.joined(separator: ", "))")
        print("  Unavailable: \(health.unavailable.joined(separator: ", "))")
        print("  Active: \(health.activeOrchestrator ?? "None")")

        // Get active orchestrator
        if let active = await manager.getActiveOrchestrator() {
            print("✓ Active orchestrator: \(active.displayName)")
        } else {
            print("✗ No orchestrator available!")
        }
    }
}
