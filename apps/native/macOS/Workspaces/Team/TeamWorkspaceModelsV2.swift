//
//  TeamWorkspaceModelsV2.swift
//  MagnetarStudio (macOS)
//
//  Shared models for TeamWorkspace_v2 - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//

import SwiftUI

// TeamMember model for TeamWorkspace_v2 (separate from main TeamWorkspace)
public struct TeamMember: Identifiable {
    public let id: String
    public let name: String
    public let role: String
    public let status: String
    public let avatar: String?

    public init(id: String, name: String, role: String, status: String, avatar: String?) {
        self.id = id
        self.name = name
        self.role = role
        self.status = status
        self.avatar = avatar
    }

    public var email: String {
        "\(name.lowercased().replacingOccurrences(of: " ", with: "."))@magnetar.studio"
    }

    public var phone: String {
        "+1 (555) 123-4567"
    }

    public var isOnline: Bool {
        status == "online"
    }

    public var lastActive: String {
        isOnline ? "Just now" : "1 hour ago"
    }

    public var initials: String {
        let parts = name.split(separator: " ")
        return parts.compactMap { $0.first }.prefix(2).map { String($0) }.joined()
    }

    public static let mockMembers = [
        TeamMember(id: "1", name: "Alice Johnson", role: "Engineering Lead", status: "online", avatar: nil),
        TeamMember(id: "2", name: "Bob Smith", role: "Senior Engineer", status: "online", avatar: nil),
        TeamMember(id: "3", name: "Carol Davis", role: "Engineer", status: "offline", avatar: nil),
        TeamMember(id: "4", name: "David Wilson", role: "Engineer", status: "online", avatar: nil),
        TeamMember(id: "5", name: "Eve Martinez", role: "Junior Engineer", status: "offline", avatar: nil)
    ]
}
