//
//  APIClient.swift
//  MagnetarStudio
//
//  HTTP client for communicating with FastAPI backend.
//  Handles authentication, retries, and error handling.
//

import Foundation

final class APIClient {
    static let shared = APIClient()

    private let baseURL = URL(string: "http://localhost:8000/api/v1")!
    private let session: URLSession
    private let keychain = KeychainManager.shared

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        self.session = URLSession(configuration: config)
    }

    // MARK: - Authentication

    func login(username: String, password: String) async throws -> AuthResponse {
        let url = baseURL.appendingPathComponent("auth/login")

        let request = LoginRequest(
            username: username,
            password: password,
            deviceFingerprint: getDeviceIdentifier()
        )

        return try await post(url: url, body: request, responseType: AuthResponse.self)
    }

    func register(username: String, password: String, email: String?) async throws -> AuthResponse {
        let url = baseURL.appendingPathComponent("auth/register")

        let request = RegisterRequest(
            username: username,
            password: password,
            email: email,
            deviceFingerprint: getDeviceIdentifier()
        )

        return try await post(url: url, body: request, responseType: AuthResponse.self)
    }

    func logout() async throws {
        let url = baseURL.appendingPathComponent("auth/logout")
        let _: LogoutResponse = try await post(url: url, body: EmptyRequest(), responseType: LogoutResponse.self)
    }

    func validateToken(_ token: String) async throws -> UserDTO {
        let url = baseURL.appendingPathComponent("auth/me")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        // UserDTO uses explicit CodingKeys

        return try decoder.decode(UserDTO.self, from: data)
    }

    func refreshToken(_ refreshToken: String) async throws -> TokenRefreshResponse {
        let url = baseURL.appendingPathComponent("auth/refresh")

        let request = RefreshTokenRequest(refreshToken: refreshToken)

        return try await post(url: url, body: request, responseType: TokenRefreshResponse.self)
    }

    // MARK: - Generic HTTP Methods

    private func post<T: Encodable, R: Decodable>(
        url: URL,
        body: T,
        responseType: R.Type
    ) async throws -> R {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if available
        if let token = try? keychain.retrieve(for: "jwt_token") {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Encode body
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(body)

        // Debug logging
        if let jsonString = String(data: request.httpBody ?? Data(), encoding: .utf8) {
            print("📤 POST \(url)")
            print("📦 Body: \(jsonString)")
        }

        // Execute request
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            // Log error response
            if let errorString = String(data: data, encoding: .utf8) {
                print("❌ HTTP \(httpResponse.statusCode): \(errorString)")
            }
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }

        // Debug success response
        if let responseString = String(data: data, encoding: .utf8) {
            print("✅ Response: \(responseString)")
        }

        // Decode response
        let decoder = JSONDecoder()
        // Note: AuthResponse uses explicit CodingKeys, so no automatic conversion needed

        return try decoder.decode(R.self, from: data)
    }

    // MARK: - Device Identifier

    private func getDeviceIdentifier() -> String? {
        #if os(macOS)
        // macOS: Use hardware UUID
        if let uuid = getMacSerialNumber() {
            return uuid
        }
        // Fallback to random persistent ID
        return UserDefaults.standard.string(forKey: "deviceIdentifier") ?? {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: "deviceIdentifier")
            return newID
        }()
        #else
        // iOS/iPadOS: Use identifierForVendor
        return UIDevice.current.identifierForVendor?.uuidString
        #endif
    }

    #if os(macOS)
    private func getMacSerialNumber() -> String? {
        let platformExpert = IOServiceGetMatchingService(
            kIOMainPortDefault,
            IOServiceMatching("IOPlatformExpertDevice")
        )

        guard platformExpert > 0 else { return nil }

        guard let serialNumber = IORegistryEntryCreateCFProperty(
            platformExpert,
            kIOPlatformSerialNumberKey as CFString,
            kCFAllocatorDefault,
            0
        ).takeUnretainedValue() as? String else {
            IOObjectRelease(platformExpert)
            return nil
        }

        IOObjectRelease(platformExpert)
        return serialNumber
    }
    #endif
}

// MARK: - Request/Response Models

struct LoginRequest: Codable {
    let username: String
    let password: String
    let deviceFingerprint: String?
}

struct RegisterRequest: Codable {
    let username: String
    let password: String
    let email: String?
    let deviceFingerprint: String?
}

struct RefreshTokenRequest: Codable {
    let refreshToken: String
}

struct EmptyRequest: Codable {}

struct AuthResponse: Codable {
    let token: String
    let refreshToken: String
    let userId: String
    let username: String
    let deviceId: String
    let role: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case token
        case refreshToken = "refresh_token"
        case userId = "user_id"
        case username
        case deviceId = "device_id"
        case role
        case expiresIn = "expires_in"
    }

    // Convert to UserDTO
    func toUserDTO() -> UserDTO {
        return UserDTO(
            id: UUID(), // Backend doesn't return UUID, using new one
            username: username,
            email: nil,
            role: role,
            createdAt: Date(),
            lastLogin: Date()
        )
    }
}

struct TokenRefreshResponse: Codable {
    let success: Bool
    let token: String
    let refreshToken: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case success, token
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
    }
}

struct LogoutResponse: Codable {
    let success: Bool
    let message: String
}

// MARK: - Error Types

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let statusCode):
            return "HTTP error: \(statusCode)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}
