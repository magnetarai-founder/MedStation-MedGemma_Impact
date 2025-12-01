//
//  PanicModeService.swift
//  MagnetarStudio
//
//  Service for emergency panic mode operations
//

import Foundation

enum PanicLevel {
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
    private let baseURL: String

    private init() {
        self.apiClient = .shared
        self.baseURL = "\(APIConfiguration.shared.versionedBaseURL)/panic"
    }

    /// Trigger standard panic mode (secure wipe via backend)
    func triggerPanicMode(level: PanicLevel = .standard, reason: String? = nil) async throws -> PanicTriggerResponse {
        switch level {
        case .standard:
            return try await triggerStandardPanic(reason: reason)
        case .emergency:
            throw PanicModeError.emergencyModeNotImplemented
        }
    }

    /// Trigger standard panic mode
    private func triggerStandardPanic(reason: String?) async throws -> PanicTriggerResponse {
        let url = URL(string: "\(baseURL)/trigger")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Inject auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Build request body
        let body = PanicTriggerRequest(
            confirmation: "CONFIRM",
            reason: reason ?? "Manual panic trigger from Swift app"
        )

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)

        // Execute request
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw PanicModeError.invalidResponse
        }

        // Handle errors
        if httpResponse.statusCode == 429 {
            throw PanicModeError.rateLimitExceeded
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw PanicModeError.backendError(httpResponse.statusCode)
        }

        // Decode response
        let decoder = JSONDecoder()
        return try decoder.decode(PanicTriggerResponse.self, from: data)
    }

    /// Get current panic mode status
    func getPanicStatus() async throws -> PanicStatusResponse {
        let url = URL(string: "\(baseURL)/status")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        // Inject auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw PanicModeError.invalidResponse
        }

        let decoder = JSONDecoder()
        return try decoder.decode(PanicStatusResponse.self, from: data)
    }
}

enum PanicModeError: LocalizedError {
    case emergencyModeNotImplemented
    case invalidResponse
    case rateLimitExceeded
    case backendError(Int)

    var errorDescription: String? {
        switch self {
        case .emergencyModeNotImplemented:
            return "Emergency mode (triple-click) not yet implemented"
        case .invalidResponse:
            return "Invalid response from panic mode API"
        case .rateLimitExceeded:
            return "Rate limit exceeded: Max 5 panic triggers per hour"
        case .backendError(let code):
            return "Backend panic mode failed with status code: \(code)"
        }
    }
}
