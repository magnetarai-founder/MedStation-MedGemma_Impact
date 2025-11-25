import Foundation

/// API User model matching /api/v1/users/me response
struct ApiUser: Codable, Identifiable {
    let userId: String
    let username: String
    let role: UserRole?
    let email: String?
    let createdAt: Date?
    let updatedAt: Date?

    var id: String { userId }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case role
        case email
        case createdAt = "created_at"
        case updatedAt = "updated_at"
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
