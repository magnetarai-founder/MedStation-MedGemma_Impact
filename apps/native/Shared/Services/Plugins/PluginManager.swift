//
//  PluginManager.swift
//  MagnetarStudio
//
//  Discovers, loads, and manages plugins.
//  Plugins are stored as bundles in ~/Library/Application Support/MagnetarStudio/plugins/
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "PluginManager")

enum PluginError: Error, LocalizedError {
    case manifestLoadFailed(String)

    var errorDescription: String? {
        switch self {
        case .manifestLoadFailed(let msg): return "Plugin manifest failed to load: \(msg)"
        }
    }
}

@MainActor
@Observable
final class PluginManager {
    static let shared = PluginManager()

    // MARK: - State

    private(set) var plugins: [InstalledPlugin] = []
    private(set) var isLoading = true

    var activePlugins: [InstalledPlugin] { plugins.filter { $0.isActive } }
    var inactivePlugins: [InstalledPlugin] { plugins.filter { !$0.isActive } }

    // MARK: - Paths

    private let pluginsDirectory: URL = {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return appSupport.appendingPathComponent("MagnetarStudio/plugins", isDirectory: true)
    }()

    private let settingsFile: URL = {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return appSupport.appendingPathComponent("MagnetarStudio/plugins/plugin_settings.json", isDirectory: false)
    }()

    private init() {}

    // MARK: - Discovery & Loading

    /// Discover and load all plugins from the plugins directory.
    func loadAll() async {
        isLoading = true
        defer { isLoading = false }

        ensureDirectory()

        // Load saved settings
        let savedSettings = loadSettings()

        // Discover plugin bundles
        var discovered: [InstalledPlugin] = []

        do {
            let contents = try FileManager.default.contentsOfDirectory(
                at: pluginsDirectory,
                includingPropertiesForKeys: [.isDirectoryKey],
                options: [.skipsHiddenFiles]
            )

            for url in contents {
                guard url.hasDirectoryPath else { continue }
                let manifestURL = url.appendingPathComponent("manifest.json")
                guard FileManager.default.fileExists(atPath: manifestURL.path) else { continue }

                do {
                    let manifest = try PluginManifest.load(from: manifestURL)
                    let settings = savedSettings[manifest.id] ?? [:]
                    let state: PluginState = (savedSettings[manifest.id] != nil) ? .active(loadedAt: Date()) : .inactive

                    let plugin = InstalledPlugin(
                        manifest: manifest,
                        bundleURL: url,
                        state: state,
                        settingValues: settings
                    )
                    discovered.append(plugin)
                    logger.info("Discovered plugin: \(manifest.name) v\(manifest.version)")
                } catch {
                    logger.error("Failed to load plugin at \(url.lastPathComponent): \(error.localizedDescription)")
                    // Create errored entry
                    let errored = InstalledPlugin(
                        manifest: PluginManifest(
                            id: url.lastPathComponent,
                            name: url.lastPathComponent,
                            version: "?",
                            author: "Unknown",
                            description: "Failed to load",
                            minAppVersion: nil,
                            capabilities: [],
                            permissions: .init(),
                            settings: []
                        ),
                        bundleURL: url,
                        state: .errored(message: error.localizedDescription),
                        settingValues: [:]
                    )
                    discovered.append(errored)
                }
            }
        } catch {
            logger.error("Failed to scan plugins directory: \(error.localizedDescription)")
        }

        // Register built-in plugins
        let builtins = BuiltinPluginAdapter.builtinPlugins()
        discovered.insert(contentsOf: builtins, at: 0)

        plugins = discovered

        // Activate plugins that should be active (includes built-ins since they start as .active)
        for plugin in plugins where plugin.isActive {
            activatePlugin(plugin.id)
        }

        logger.info("Loaded \(self.plugins.count) plugins (\(self.activePlugins.count) active)")
    }

    // MARK: - Activation / Deactivation

    func togglePlugin(_ pluginId: String) {
        guard let index = plugins.firstIndex(where: { $0.id == pluginId }) else { return }
        if plugins[index].isActive {
            deactivatePlugin(pluginId)
        } else {
            activatePlugin(pluginId)
        }
    }

    func activatePlugin(_ pluginId: String) {
        guard let index = plugins.firstIndex(where: { $0.id == pluginId }) else { return }
        plugins[index].state = .active(loadedAt: Date())

        // Register capabilities
        let plugin = plugins[index]
        for capability in plugin.manifest.capabilities {
            registerCapability(capability, plugin: plugin)
        }

        saveSettings()
        logger.info("Activated plugin: \(plugin.name)")
    }

    func deactivatePlugin(_ pluginId: String) {
        guard let index = plugins.firstIndex(where: { $0.id == pluginId }) else { return }
        plugins[index].state = .inactive

        // Unregister capabilities
        PluginRegistry.shared.unregisterAll(pluginId: pluginId)

        saveSettings()
        let pluginName = plugins[index].name
        logger.info("Deactivated plugin: \(pluginName)")
    }

    // MARK: - Settings

    func updateSetting(pluginId: String, key: String, value: String) {
        guard let index = plugins.firstIndex(where: { $0.id == pluginId }) else { return }
        plugins[index].settingValues[key] = value
        saveSettings()
    }

    // MARK: - Install / Uninstall

    func installPlugin(from sourceURL: URL) async throws {
        let destURL = pluginsDirectory.appendingPathComponent(sourceURL.lastPathComponent)
        try FileManager.default.copyItem(at: sourceURL, to: destURL)
        logger.info("Installed plugin from \(sourceURL.lastPathComponent)")

        await loadAll()

        // Verify the new plugin loaded without errors
        let pluginDir = destURL.lastPathComponent
        if let plugin = plugins.first(where: { $0.bundleURL.lastPathComponent == pluginDir }),
           case .errored(let msg) = plugin.state {
            throw PluginError.manifestLoadFailed(msg)
        }
    }

    func uninstallPlugin(_ pluginId: String) throws {
        guard let plugin = plugins.first(where: { $0.id == pluginId }) else { return }

        // Don't uninstall built-ins
        guard !plugin.manifest.id.hasPrefix("com.magnetar.builtin.") else {
            logger.warning("Cannot uninstall built-in plugin: \(plugin.name)")
            return
        }

        deactivatePlugin(pluginId)
        try FileManager.default.removeItem(at: plugin.bundleURL)
        plugins.removeAll { $0.id == pluginId }
        saveSettings()
        logger.info("Uninstalled plugin: \(plugin.name)")
    }

    // MARK: - Private Helpers

    private func ensureDirectory() {
        PersistenceHelpers.ensureDirectory(at: pluginsDirectory, label: "plugins directory")
    }

    private func registerCapability(_ capability: PluginCapability, plugin: InstalledPlugin) {
        // Built-in plugins handle their own registration via BuiltinPluginAdapter
        // External plugins would register via their bundle's entry point
        logger.debug("Registered capability \(capability.rawValue) for \(plugin.name)")
    }

    // MARK: - Persistence

    private func loadSettings() -> [String: [String: String]] {
        guard FileManager.default.fileExists(atPath: settingsFile.path) else { return [:] }
        do {
            let data = try Data(contentsOf: settingsFile)
            return try JSONDecoder().decode([String: [String: String]].self, from: data)
        } catch {
            logger.error("Failed to load plugin settings: \(error.localizedDescription)")
            return [:]
        }
    }

    private func saveSettings() {
        let settings = Dictionary(uniqueKeysWithValues: plugins.filter { $0.isActive }.map {
            ($0.id, $0.settingValues)
        })
        do {
            ensureDirectory()
            let data = try JSONEncoder().encode(settings)
            try data.write(to: settingsFile, options: .atomic)
        } catch {
            logger.error("Failed to save plugin settings: \(error.localizedDescription)")
        }
    }
}
