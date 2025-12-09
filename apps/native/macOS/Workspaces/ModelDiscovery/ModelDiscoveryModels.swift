//
//  ModelDiscoveryModels.swift
//  MagnetarStudio (macOS)
//
//  Filter and sort options for model discovery - Extracted from ModelDiscoveryWorkspace.swift
//

import Foundation

// MARK: - Model Type Filter

enum ModelTypeFilter: String, CaseIterable {
    case all = "all"
    case official = "official"
    case community = "community"

    var displayName: String {
        switch self {
        case .all: return "All"
        case .official: return "Official"
        case .community: return "Community"
        }
    }

    var apiValue: String? {
        self == .all ? nil : self.rawValue
    }
}

// MARK: - Capability Filter

enum CapabilityFilter: String, CaseIterable {
    case all = "all"
    case code = "code"
    case chat = "chat"
    case vision = "vision"
    case embedding = "embedding"

    var displayName: String {
        switch self {
        case .all: return "All"
        case .code: return "Code"
        case .chat: return "Chat"
        case .vision: return "Vision"
        case .embedding: return "Embedding"
        }
    }

    var apiValue: String? {
        self == .all ? nil : self.rawValue
    }
}

// MARK: - Sort Option

enum SortOption: String, CaseIterable {
    case pulls = "pulls"
    case lastUpdated = "last_updated"

    var displayName: String {
        switch self {
        case .pulls: return "Most Popular"
        case .lastUpdated: return "Recently Updated"
        }
    }

    var apiValue: String {
        self.rawValue
    }
}
