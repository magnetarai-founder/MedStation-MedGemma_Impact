//
//  PluginManifest.swift
//  MagnetarStudio
//
//  Plugin manifest model — describes a plugin's identity, version, and capabilities.
//  Loaded from plugin bundle's manifest.json.
//

import Foundation

// MARK: - Plugin Capability

/// Extension points a plugin can provide.
enum PluginCapability: String, Codable, CaseIterable, Identifiable, Sendable {
    case blockType = "block_type"
    case aiStrategy = "ai_strategy"
    case exportFormat = "export_format"
    case automationAction = "automation_action"
    case chartType = "chart_type"
    case theme = "theme"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .blockType: return "Block Type"
        case .aiStrategy: return "AI Strategy"
        case .exportFormat: return "Export Format"
        case .automationAction: return "Automation Action"
        case .chartType: return "Chart Type"
        case .theme: return "Theme"
        }
    }

    var icon: String {
        switch self {
        case .blockType: return "cube"
        case .aiStrategy: return "sparkles"
        case .exportFormat: return "arrow.up.doc"
        case .automationAction: return "gearshape"
        case .chartType: return "chart.bar"
        case .theme: return "paintpalette"
        }
    }
}

// MARK: - Plugin State

/// Runtime state of a plugin — encodes status with associated context data.
enum PluginState: Sendable, Equatable {
    case active(loadedAt: Date)
    case inactive
    case errored(message: String)
    case incompatible

    var isActive: Bool {
        if case .active = self { return true } else { return false }
    }

    var displayName: String {
        switch self {
        case .active: return "Active"
        case .inactive: return "Inactive"
        case .errored: return "Errored"
        case .incompatible: return "Incompatible"
        }
    }

    var loadedAt: Date? {
        if case .active(let date) = self { return date } else { return nil }
    }

    var errorMessage: String? {
        if case .errored(let msg) = self { return msg } else { return nil }
    }
}

// MARK: - Plugin Setting

/// A configurable setting defined by the plugin manifest.
struct PluginSetting: Codable, Identifiable, Sendable {
    let id: String
    let label: String
    let description: String
    let type: SettingType
    let defaultValue: String
    var choices: [String]?

    enum SettingType: String, Codable, Sendable {
        case text
        case number
        case boolean
        case choice
    }
}

// MARK: - Plugin Manifest

/// Describes a plugin: identity, capabilities, permissions, and settings.
struct PluginManifest: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let version: String
    let author: String
    let description: String
    let minAppVersion: String?
    let capabilities: [PluginCapability]
    let permissions: PluginPermissions
    let settings: [PluginSetting]

    /// Icon SF Symbol name (defaults to "puzzlepiece.extension")
    var icon: String?

    struct PluginPermissions: Codable, Sendable {
        /// Plugin can access the network
        var network: Bool = false
        /// Plugin can read files from user's filesystem
        var fileRead: Bool = false
        /// Plugin can write files to user's filesystem
        var fileWrite: Bool = false
        /// Plugin can access clipboard
        var clipboard: Bool = false
    }

    // MARK: - Loading

    /// Load manifest from a JSON file URL.
    static func load(from url: URL) throws -> PluginManifest {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(PluginManifest.self, from: data)
    }
}

// MARK: - Installed Plugin

/// Runtime representation of an installed plugin with its manifest and state.
struct InstalledPlugin: Identifiable, Sendable {
    let manifest: PluginManifest
    let bundleURL: URL
    var state: PluginState
    var settingValues: [String: String]

    var id: String { manifest.id }
    var name: String { manifest.name }
    var version: String { manifest.version }
    var isActive: Bool { state.isActive }

    var icon: String { manifest.icon ?? "puzzlepiece.extension" }

    /// Get a setting value, falling back to manifest default.
    func settingValue(for key: String) -> String {
        if let value = settingValues[key] { return value }
        return manifest.settings.first { $0.id == key }?.defaultValue ?? ""
    }
}
