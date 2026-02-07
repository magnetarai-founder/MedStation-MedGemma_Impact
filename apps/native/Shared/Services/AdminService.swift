//
//  AdminService.swift
//  MagnetarStudio
//
//  Service layer for Founder Admin endpoints.
//  All endpoints require founder_rights (or admin/super_admin) on the backend.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AdminService")

// MARK: - Admin Service

final class AdminService {
    static let shared = AdminService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Users

    func fetchUsers() async throws -> AdminUsersResponse {
        try await apiClient.request("/v1/admin/users")
    }

    func resetPassword(userId: String) async throws {
        let _: EmptyAdminResponse = try await apiClient.request(
            "/v1/admin/users/\(userId)/reset-password",
            method: .post
        )
    }

    func unlockAccount(userId: String) async throws {
        let _: EmptyAdminResponse = try await apiClient.request(
            "/v1/admin/users/\(userId)/unlock",
            method: .post
        )
    }

    // MARK: - Device Overview

    func fetchDeviceOverview() async throws -> DeviceOverviewResponse {
        try await apiClient.request("/v1/admin/device/overview")
    }

    // MARK: - Audit Logs

    func fetchAuditLogs(
        limit: Int = 100,
        offset: Int = 0,
        userId: String? = nil,
        action: String? = nil
    ) async throws -> AuditLogsResponse {
        // Build query string manually since apiClient.request doesn't support query params
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)")
        ]
        if let userId {
            components.queryItems?.append(URLQueryItem(name: "user_id", value: userId))
        }
        if let action {
            components.queryItems?.append(URLQueryItem(name: "action", value: action))
        }

        let queryString = components.percentEncodedQuery ?? ""
        let path = "/v1/admin/audit/logs?\(queryString)"

        return try await apiClient.request(path)
    }
}

// MARK: - Response Models

/// Placeholder for endpoints that return { status: "...", message: "..." }
private struct EmptyAdminResponse: Decodable, Sendable {
    let status: String?
    let message: String?
}

// MARK: - Users

struct AdminUsersResponse: Codable, Sendable {
    let users: [AdminUser]
    let total: Int
}

struct AdminUser: Codable, Sendable, Identifiable {
    let userId: String
    let username: String
    let deviceId: String
    let createdAt: String
    let lastLogin: String?
    let isActive: Bool
    let role: String?

    var id: String { userId }

    /// Parse role string into UserRole enum
    var userRole: UserRole? {
        guard let role else { return nil }
        return UserRole(rawValue: role)
    }

    /// Whether the user appears recently active (last login within 30 minutes)
    var isRecentlyActive: Bool {
        guard let lastLogin else { return false }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: lastLogin) else {
            // Try without fractional seconds
            formatter.formatOptions = [.withInternetDateTime]
            guard let date = formatter.date(from: lastLogin) else { return false }
            return Date().timeIntervalSince(date) < 30 * 60
        }
        return Date().timeIntervalSince(date) < 30 * 60
    }

    /// Relative time string for last login
    var lastLoginRelative: String {
        guard let lastLogin else { return "Never" }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let date = formatter.date(from: lastLogin) ?? {
            formatter.formatOptions = [.withInternetDateTime]
            return formatter.date(from: lastLogin)
        }()
        guard let date else { return lastLogin }

        let elapsed = Date().timeIntervalSince(date)
        if elapsed < 60 { return "Just now" }
        if elapsed < 3600 { return "\(Int(elapsed / 60))m ago" }
        if elapsed < 86400 { return "\(Int(elapsed / 3600))h ago" }
        return "\(Int(elapsed / 86400))d ago"
    }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case username
        case deviceId = "device_id"
        case createdAt = "created_at"
        case lastLogin = "last_login"
        case isActive = "is_active"
        case role
    }
}

// MARK: - Device Overview

struct DeviceOverviewResponse: Codable, Sendable {
    let deviceOverview: DeviceOverview
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case deviceOverview = "device_overview"
        case timestamp
    }
}

struct DeviceOverview: Codable, Sendable {
    let totalUsers: Int?
    let totalChatSessions: Int?
    let totalWorkflows: Int?
    let totalWorkItems: Int?
    let totalDocuments: Int?
    let dataDirSizeBytes: Int?
    let dataDirSizeMb: Double?

    enum CodingKeys: String, CodingKey {
        case totalUsers = "total_users"
        case totalChatSessions = "total_chat_sessions"
        case totalWorkflows = "total_workflows"
        case totalWorkItems = "total_work_items"
        case totalDocuments = "total_documents"
        case dataDirSizeBytes = "data_dir_size_bytes"
        case dataDirSizeMb = "data_dir_size_mb"
    }
}

// MARK: - Audit Logs

struct AuditLogsResponse: Codable, Sendable {
    let logs: [AuditLogEntry]
    let total: Int
}

struct AuditLogEntry: Codable, Sendable, Identifiable {
    let id: Int
    let userId: String
    let action: String
    let resource: String
    let resourceId: String
    let timestamp: String
    let ipAddress: String?
    let details: String?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case action
        case resource
        case resourceId = "resource_id"
        case timestamp
        case ipAddress = "ip_address"
        case details
    }
}
