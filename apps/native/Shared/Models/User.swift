import Foundation

/// API User model matching /api/v1/auth/me response
struct ApiUser: Codable, Identifiable {
    let userId: String
    let username: String
    let deviceId: String
    let role: String

    var id: String { userId }

    var userRole: UserRole? {
        UserRole(rawValue: role)
    }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case deviceId = "device_id"
        case role
    }
}

/// User roles in the system
enum UserRole: String, Codable {
    case member
    case admin
    case superAdmin = "super_admin"
    case founderRights = "founder_rights"

    var displayName: String {
        switch self {
        case .member: return "Member"
        case .admin: return "Admin"
        case .superAdmin: return "Super Admin"
        case .founderRights: return "Founder"
        }
    }
}

/// Setup status response from /api/v1/users/me/setup/status
struct SetupStatus: Codable {
    let userSetupCompleted: Bool

    enum CodingKeys: String, CodingKey {
        case userSetupCompleted = "user_setup_completed"
    }
}
