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
        // Log via SecurityManager (which sends to backend)
        SecurityManager.shared.logSecurityEvent(SecurityEvent(
            type: .panicTriggered,
            level: .emergency,
            message: "Emergency mode triggered via \(method.rawValue)",
            details: [
                "reason": reason ?? "User-initiated",
                "simulation": isSimulationMode ? "true" : "false",
                "trigger_method": method.rawValue
            ]
        ))
    }

    func sendEmergencyLogToRemote(reason: String?) async throws {
        // Send emergency log directly to backend audit API
        // Non-blocking - don't fail if network unavailable
        do {
            let url = URL(string: "\(APIConfiguration.shared.versionedBaseURL)/audit/log")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            // Add auth token if available
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let auditPayload: [String: Any] = [
                "action": "security.emergency_mode_activated",
                "details": [
                    "reason": reason ?? "User-initiated",
                    "simulation": isSimulationMode,
                    "timestamp": ISO8601DateFormatter().string(from: Date())
                ]
            ]
            request.httpBody = try JSONSerialization.data(withJSONObject: auditPayload)

            // Short timeout - don't block emergency operations
            request.timeoutInterval = 3.0

            let (_, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 201 {
                    print("✅ Emergency log sent to backend")
                } else {
                    print("⚠️ Emergency log response: \(httpResponse.statusCode)")
                }
            }
        } catch {
            // Don't fail emergency operations due to logging
            print("⚠️ Failed to send emergency log to backend (continuing): \(error.localizedDescription)")
        }
    }
}
