//
//  EmergencyModeService+Backend.swift
//  MagnetarStudio
//
//  Extension for backend API integration
//  Handles communication with backend emergency endpoints
//

import Foundation

// MARK: - Backend Integration

extension EmergencyModeService {

    func callBackendEmergencyWipe(reason: String?) async throws -> BackendEmergencyResponse {
        struct EmergencyWipeRequest: Codable {
            let confirmation: String
            let reason: String
        }

        let request = EmergencyWipeRequest(
            confirmation: "CONFIRM",
            reason: reason ?? "User-initiated emergency mode"
        )

        return try await apiClient.request(
            "/api/v1/panic/emergency",
            method: .post,
            body: request,
            authenticated: true
        )
    }
}

// MARK: - Audit Logging

extension EmergencyModeService {

    func logEmergencyTrigger(reason: String?, method: EmergencyTriggerMethod) async {
        // TODO: Integrate with SecurityManager when available
        print("🔒 Security Event: Emergency mode triggered via \(method.rawValue)")
        print("   Reason: \(reason ?? "User-initiated")")
        print("   Simulation: \(isSimulationMode ? "true" : "false")")
    }

    func sendEmergencyLogToRemote(reason: String?) async throws {
        // TODO: Implement remote emergency log
        // Send to backend if network available
        // Don't block if network fails
        print("⚠️ TODO: Remote emergency log not implemented yet")
    }
}
