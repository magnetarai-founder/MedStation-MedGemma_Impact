//
//  FeatureFlags.swift
//  MagnetarStudio
//
//  Phase 2D: Feature flags for optional features
//  Controls which spawnable workspaces are available in the Quick Action menu
//
//  Core features (always ON): chat, files
//  Optional features (OFF by default): project_management, automations, data_analysis
//

import Foundation
import Observation

// MARK: - Feature Flags

/// Feature flags to control optional features
/// Stored in UserDefaults for persistence across sessions
@MainActor
@Observable
final class FeatureFlags {
    static let shared = FeatureFlags()

    // MARK: - Core Features (Always ON)
    // These cannot be disabled

    let chat: Bool = true
    let files: Bool = true

    // MARK: - Optional Features (OFF by default)
    // Users can enable these in Settings

    /// Team workspace - collaboration features
    var team: Bool {
        didSet { save(key: "feature.team", value: team) }
    }

    /// Code workspace - code editor and IDE features
    var code: Bool {
        didSet { save(key: "feature.code", value: code) }
    }

    /// Project Management - Kanban boards, task tracking
    var projectManagement: Bool {
        didSet { save(key: "feature.projectManagement", value: projectManagement) }
    }

    /// Automations - Workflow builder
    var automations: Bool {
        didSet { save(key: "feature.automations", value: automations) }
    }

    /// Data Analysis - Database workspace, SQL queries
    var dataAnalysis: Bool {
        didSet { save(key: "feature.dataAnalysis", value: dataAnalysis) }
    }

    /// Voice Transcription - Insights workspace (key differentiator, ON by default)
    var voiceTranscription: Bool {
        didSet { save(key: "feature.voiceTranscription", value: voiceTranscription) }
    }

    /// MagnetarTrust - Trust network for churches and missions
    var trust: Bool {
        didSet { save(key: "feature.trust", value: trust) }
    }

    /// MagnetarHub - Admin and hub features
    var magnetarHub: Bool {
        didSet { save(key: "feature.magnetarHub", value: magnetarHub) }
    }

    // MARK: - Initialization

    private init() {
        // Load saved values or use defaults
        self.team = UserDefaults.standard.object(forKey: "feature.team") as? Bool ?? false
        self.code = UserDefaults.standard.object(forKey: "feature.code") as? Bool ?? true
        self.projectManagement = UserDefaults.standard.object(forKey: "feature.projectManagement") as? Bool ?? true
        self.automations = UserDefaults.standard.object(forKey: "feature.automations") as? Bool ?? true
        self.dataAnalysis = UserDefaults.standard.object(forKey: "feature.dataAnalysis") as? Bool ?? true
        self.voiceTranscription = UserDefaults.standard.object(forKey: "feature.voiceTranscription") as? Bool ?? true  // ON by default
        self.trust = UserDefaults.standard.object(forKey: "feature.trust") as? Bool ?? false
        self.magnetarHub = UserDefaults.standard.object(forKey: "feature.magnetarHub") as? Bool ?? false
    }

    // MARK: - Persistence

    private func save(key: String, value: Bool) {
        UserDefaults.standard.set(value, forKey: key)
    }

    // MARK: - Workspace Helpers

    /// Check if a workspace is enabled
    func isWorkspaceEnabled(_ workspace: Workspace) -> Bool {
        switch workspace {
        // Core workspaces - always enabled
        case .chat, .files, .workspace:
            return true

        // Optional workspaces - check flags
        case .code:
            return true  // Core tab, always enabled
        case .kanban:
            return projectManagement
        case .database:
            return dataAnalysis
        case .insights:
            return voiceTranscription
        case .trust:
            return trust
        case .magnetarHub:
            return magnetarHub
        case .team:
            return team  // Legacy
        }
    }

    /// Get enabled spawnable workspaces
    var enabledSpawnableWorkspaces: [Workspace] {
        Workspace.spawnableWorkspaces.filter { isWorkspaceEnabled($0) }
    }

    // MARK: - Bulk Operations

    /// Enable all optional features (except team — future upgrade)
    func enableAll() {
        // team intentionally excluded — coming in a future upgrade
        code = true
        projectManagement = true
        automations = true
        dataAnalysis = true
        voiceTranscription = true
        trust = true
        magnetarHub = true
    }

    /// Reset to defaults (most features OFF)
    func resetToDefaults() {
        team = false
        code = true
        projectManagement = true
        automations = false
        dataAnalysis = true
        voiceTranscription = true  // Key differentiator stays ON
        trust = false
        magnetarHub = false
    }
}
