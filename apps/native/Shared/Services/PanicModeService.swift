//
//  PanicModeService.swift
//  MagnetarStudio
//
//  Service for emergency panic mode operations
//

import Foundation

public enum PanicLevel: String, Codable, Sendable {
    case standard    // Double-click: secure wipe via backend
    case emergency   // Triple-click: DoD 7-pass wipe + uninstall (NOT YET IMPLEMENTED)
}

struct PanicTriggerRequest: Codable {
    let confirmation: String
    let reason: String?
}

struct PanicTriggerResponse: Codable {
    let panicActivated: Bool
    let timestamp: String
    let reason: String
    let actionsTaken: [String]
    let errors: [String]
    let status: String

    enum CodingKeys: String, CodingKey {
        case panicActivated = "panic_activated"
        case timestamp
        case reason
        case actionsTaken = "actions_taken"
        case errors
        case status
    }
}

struct PanicStatusResponse: Codable {
    let panicActive: Bool
    let lastPanic: String?
    let secureMode: Bool

    enum CodingKeys: String, CodingKey {
        case panicActive = "panic_active"
        case lastPanic = "last_panic"
        case secureMode = "secure_mode"
    }
}

final class PanicModeService {
    static let shared = PanicModeService()

    private let apiClient: ApiClient

    private init() {
        self.apiClient = .shared
    }

    /// Trigger panic mode (standard or emergency)
    func triggerPanicMode(level: PanicLevel = .standard, reason: String? = nil) async throws -> PanicTriggerResponse {
        switch level {
        case .standard:
            return try await triggerStandardPanic(reason: reason)
        case .emergency:
            // Delegate to EmergencyModeService for DoD 7-pass wipe + self-uninstall
            return try await triggerEmergencyPanic(reason: reason)
        }
    }

    /// Trigger emergency panic mode (DoD 7-pass wipe + self-uninstall)
    /// CRITICAL: This is IRREVERSIBLE in production
    private func triggerEmergencyPanic(reason: String?) async throws -> PanicTriggerResponse {
        do {
            let report = try await EmergencyModeService.shared.triggerEmergency(
                reason: reason,
                confirmationMethod: .tripleClick
            )

            return PanicTriggerResponse(
                panicActivated: true,
                timestamp: ISO8601DateFormatter().string(from: Date()),
                reason: reason ?? "Emergency mode triggered",
                actionsTaken: [
                    "DoD 7-pass wipe initiated",
                    "\(report.filesWiped) files wiped",
                    report.simulated ? "SIMULATION MODE - no files actually deleted" : "Files permanently destroyed"
                ],
                errors: report.errors,
                status: report.errors.isEmpty ? "completed" : "completed_with_errors"
            )
        } catch let error as EmergencyModeError {
            throw PanicModeError.emergencyModeFailed(errors: [error.localizedDescription])
        }
    }

    /// Trigger standard panic mode
    private func triggerStandardPanic(reason: String?) async throws -> PanicTriggerResponse {
        let body = PanicTriggerRequest(
            confirmation: "CONFIRM",
            reason: reason ?? "Manual panic trigger from Swift app"
        )

        return try await apiClient.request(
            "/api/v1/panic/trigger",
            method: .post,
            body: body,
            authenticated: true
        )
    }

    /// Get current panic mode status
    func getPanicStatus() async throws -> PanicStatusResponse {
        return try await apiClient.request(
            "/api/v1/panic/status",
            method: .get,
            authenticated: true
        )
    }
}

enum PanicModeError: LocalizedError {
    case emergencyModeNotImplemented
    case emergencyModeFailed(errors: [String])
    case invalidResponse
    case rateLimitExceeded
    case backendError(Int)

    var errorDescription: String? {
        switch self {
        case .emergencyModeNotImplemented:
            return "Emergency mode (triple-click) not yet implemented"
        case .emergencyModeFailed(let errors):
            return "Emergency mode completed with errors: \(errors.joined(separator: ", "))"
        case .invalidResponse:
            return "Invalid response from panic mode API"
        case .rateLimitExceeded:
            return "Rate limit exceeded: Max 5 panic triggers per hour"
        case .backendError(let code):
            return "Backend panic mode failed with status code: \(code)"
        }
    }
}
