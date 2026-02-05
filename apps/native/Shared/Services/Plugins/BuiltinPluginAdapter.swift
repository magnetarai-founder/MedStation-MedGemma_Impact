//
//  BuiltinPluginAdapter.swift
//  MagnetarStudio
//
//  Wraps existing app features as built-in plugins.
//  Validates the plugin API by exercising it with real functionality.
//

import Foundation

// MARK: - Built-in Plugin Definitions

struct BuiltinPluginAdapter {
    /// Create InstalledPlugin entries for all built-in features.
    static func builtinPlugins() -> [InstalledPlugin] {
        [
            exportPlugin(),
            chartsPlugin(),
            automationPlugin(),
            aiPlugin(),
        ]
    }

    // MARK: - Export Plugin

    private static func exportPlugin() -> InstalledPlugin {
        InstalledPlugin(
            manifest: PluginManifest(
                id: "com.magnetar.builtin.export",
                name: "Export & Publishing",
                version: "1.0.0",
                author: "MagnetarStudio",
                description: "Export documents to PDF, Markdown, HTML, and CSV",
                minAppVersion: nil,
                capabilities: [.exportFormat],
                permissions: .init(fileWrite: true),
                settings: [],
                icon: "arrow.up.doc"
            ),
            bundleURL: Bundle.main.bundleURL,
            state: .active(loadedAt: Date()),
            settingValues: [:]
        )
    }

    // MARK: - Charts Plugin

    private static func chartsPlugin() -> InstalledPlugin {
        InstalledPlugin(
            manifest: PluginManifest(
                id: "com.magnetar.builtin.charts",
                name: "Data Visualization",
                version: "1.0.0",
                author: "MagnetarStudio",
                description: "Bar, line, pie, scatter, area, and donut charts via Swift Charts",
                minAppVersion: nil,
                capabilities: [.chartType, .blockType],
                permissions: .init(),
                settings: [],
                icon: "chart.bar"
            ),
            bundleURL: Bundle.main.bundleURL,
            state: .active(loadedAt: Date()),
            settingValues: [:]
        )
    }

    // MARK: - Automation Plugin

    private static func automationPlugin() -> InstalledPlugin {
        InstalledPlugin(
            manifest: PluginManifest(
                id: "com.magnetar.builtin.automation",
                name: "Workspace Automation",
                version: "1.0.0",
                author: "MagnetarStudio",
                description: "Rule-based automation with triggers, conditions, and actions",
                minAppVersion: nil,
                capabilities: [.automationAction],
                permissions: .init(),
                settings: [],
                icon: "gearshape.2"
            ),
            bundleURL: Bundle.main.bundleURL,
            state: .active(loadedAt: Date()),
            settingValues: [:]
        )
    }

    // MARK: - AI Plugin

    private static func aiPlugin() -> InstalledPlugin {
        InstalledPlugin(
            manifest: PluginManifest(
                id: "com.magnetar.builtin.ai",
                name: "AI Workspace Assistant",
                version: "1.0.0",
                author: "MagnetarStudio",
                description: "AI-powered writing, formula generation, transcription, and automation",
                minAppVersion: nil,
                capabilities: [.aiStrategy],
                permissions: .init(network: true),
                settings: [],
                icon: "sparkles"
            ),
            bundleURL: Bundle.main.bundleURL,
            state: .active(loadedAt: Date()),
            settingValues: [:]
        )
    }
}
