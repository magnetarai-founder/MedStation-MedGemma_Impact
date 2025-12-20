import Foundation

/// Auth service for login/register operations
final class AuthService {
    static let shared = AuthService()

    private let apiClient = ApiClient.shared
    private let deviceId: String

    private init() {
        // Generate or load persistent device ID
        let key = "magnetar.device_id"
        if let existing = UserDefaults.standard.string(forKey: key) {
            self.deviceId = existing
        } else {
            let newId = UUID().uuidString
            UserDefaults.standard.set(newId, forKey: key)
            self.deviceId = newId
        }
    }

    // MARK: - Auth Operations

    /// Register a new user
    func register(username: String, password: String) async throws -> LoginResponse {
        let request = RegisterRequest(
            username: username,
            password: password,
            deviceId: deviceId
        )

        let _: UserResponse = try await apiClient.request(
            "/v1/auth/register",
            method: .post,
            body: request,
            authenticated: false
        )

        // Then automatically log them in
        return try await login(username: username, password: password)
    }

    /// Login existing user
    func login(username: String, password: String) async throws -> LoginResponse {
        let request = LoginRequest(
            username: username,
            password: password,
            deviceFingerprint: deviceId
        )

        let response: LoginResponse = try await apiClient.request(
            "/v1/auth/login",
            method: .post,
            body: request,
            authenticated: false
        )

        return response
    }

    /// Check if initial setup is needed
    func checkSetupNeeded() async throws -> Bool {
        let response: SetupNeededResponse = try await apiClient.request(
            "/v1/auth/setup-needed",
            method: .get,
            authenticated: false
        )
        return response.setupNeeded
    }
}

// MARK: - Request Models

struct RegisterRequest: Codable {
    let username: String
    let password: String
    let deviceId: String
}

struct LoginRequest: Codable {
    let username: String
    let password: String
    let deviceFingerprint: String?
}

// MARK: - Response Models

struct LoginResponse: Codable {
    let token: String
    let refreshToken: String?
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
}

struct UserResponse: Codable {
    let userId: String
    let username: String
    let deviceId: String
    let role: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case deviceId = "device_id"
        case role
    }
}

struct SetupNeededResponse: Codable {
    let setupNeeded: Bool
}
