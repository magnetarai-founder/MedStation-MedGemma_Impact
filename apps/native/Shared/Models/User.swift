//
//  User.swift
//  MagnetarStudio
//
//  Created on 2025-11-23.
//

import Foundation
import SwiftData

/// User model matching backend schema
@Model
final class User {
    @Attribute(.unique) var id: UUID
    var username: String
    var email: String?
    var role: String
    var createdAt: Date
    var lastLogin: Date?

    init(
        id: UUID,
        username: String,
        email: String? = nil,
        role: String,
        createdAt: Date = Date(),
        lastLogin: Date? = nil
    ) {
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.createdAt = createdAt
        self.lastLogin = lastLogin
    }
}

// MARK: - API DTO (Data Transfer Object)

/// Codable representation of User for API responses
struct UserDTO: Codable {
    let id: UUID
    let username: String
    let email: String?
    let role: String
    let createdAt: Date
    let lastLogin: Date?

    enum CodingKeys: String, CodingKey {
        case id, username, email, role
        case createdAt = "created_at"
        case lastLogin = "last_login"
    }

    /// Convert DTO to SwiftData User model
    func toModel() -> User {
        return User(
            id: id,
            username: username,
            email: email,
            role: role,
            createdAt: createdAt,
            lastLogin: lastLogin
        )
    }
}

extension User {
    /// Convert SwiftData model to DTO for API requests
    func toDTO() -> UserDTO {
        return UserDTO(
            id: id,
            username: username,
            email: email,
            role: role,
            createdAt: createdAt,
            lastLogin: lastLogin
        )
    }
}

// MARK: - User Role
enum UserRole: String, Codable {
    case founder = "founder_rights"
    case admin = "admin"
    case member = "member"

    var displayName: String {
        switch self {
        case .founder: return "Founder"
        case .admin: return "Administrator"
        case .member: return "Member"
        }
    }

    var canAccessAdmin: Bool {
        self == .founder || self == .admin
    }
}
