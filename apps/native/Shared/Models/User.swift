import Foundation

/// API User model matching /api/v1/auth/me response
struct ApiUser: Codable, Identifiable, Sendable {
    let userId: String
    let username: String
    let deviceId: String
    let role: String

    var id: String { userId }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case deviceId = "device_id"
        case role
    }
}

