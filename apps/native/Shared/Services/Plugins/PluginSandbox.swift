//
//  PluginSandbox.swift
//  MagnetarStudio
//
//  Security sandbox for plugin execution.
//  Restricts filesystem access, network access, and resource usage.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "PluginSandbox")

// MARK: - Sandbox Error

enum PluginSandboxError: Error, LocalizedError {
    case accessDenied(resource: String)
    case networkNotPermitted
    case fileReadNotPermitted(path: String)
    case fileWriteNotPermitted(path: String)
    case clipboardNotPermitted
    case resourceLimitExceeded(limit: String)
    case invalidPath(path: String)

    var errorDescription: String? {
        switch self {
        case .accessDenied(let resource):
            return "Access denied: \(resource)"
        case .networkNotPermitted:
            return "Plugin does not have network permission"
        case .fileReadNotPermitted(let path):
            return "Plugin cannot read file: \(path)"
        case .fileWriteNotPermitted(let path):
            return "Plugin cannot write file: \(path)"
        case .clipboardNotPermitted:
            return "Plugin does not have clipboard permission"
        case .resourceLimitExceeded(let limit):
            return "Resource limit exceeded: \(limit)"
        case .invalidPath(let path):
            return "Invalid file path: \(path) (path traversal detected)"
        }
    }
}

// MARK: - Sandbox

/// Security sandbox that enforces plugin permissions.
struct PluginSandbox: Sendable {
    let pluginId: String
    let bundleURL: URL
    let permissions: PluginManifest.PluginPermissions

    /// The plugin's private data directory.
    var dataDirectory: URL {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return appSupport.appendingPathComponent("MagnetarStudio/plugin_data/\(pluginId)", isDirectory: true)
    }

    // MARK: - Filesystem Guards

    /// Check if the plugin can read from the given path.
    func validateRead(at path: URL) throws {
        let resolved = path.standardizedFileURL.path
        let bundlePath = bundleURL.standardizedFileURL.path
        let dataPath = dataDirectory.standardizedFileURL.path

        // Always allow reading from plugin's own bundle or data directory
        if resolved.hasPrefix(bundlePath) || resolved.hasPrefix(dataPath) { return }

        // External file read requires permission
        guard permissions.fileRead else {
            throw PluginSandboxError.fileReadNotPermitted(path: path.lastPathComponent)
        }

        logger.debug("Plugin \(pluginId) reading external file: \(path.lastPathComponent)")
    }

    /// Check if the plugin can write to the given path.
    func validateWrite(at path: URL) throws {
        let resolved = path.standardizedFileURL.path
        let dataPath = dataDirectory.standardizedFileURL.path

        // Always allow writing to plugin's data directory
        if resolved.hasPrefix(dataPath) { return }

        // All other writes require permission
        guard permissions.fileWrite else {
            throw PluginSandboxError.fileWriteNotPermitted(path: path.lastPathComponent)
        }

        logger.debug("Plugin \(pluginId) writing external file: \(path.lastPathComponent)")
    }

    // MARK: - Network Guard

    /// Check if the plugin can make network requests.
    func validateNetwork() throws {
        guard permissions.network else {
            throw PluginSandboxError.networkNotPermitted
        }
    }

    // MARK: - Clipboard Guard

    func validateClipboard() throws {
        guard permissions.clipboard else {
            throw PluginSandboxError.clipboardNotPermitted
        }
    }

    // MARK: - Data Directory

    /// Ensure the plugin's data directory exists.
    func ensureDataDirectory() throws {
        try FileManager.default.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
    }

    /// Read a file from the plugin's data directory.
    func readData(filename: String) throws -> Data {
        let url = dataDirectory.appendingPathComponent(filename)
        try validateRead(at: url)
        return try Data(contentsOf: url)
    }

    /// Write data to the plugin's data directory.
    func writeData(_ data: Data, filename: String) throws {
        try ensureDataDirectory()
        let url = dataDirectory.appendingPathComponent(filename)
        try validateWrite(at: url)
        try data.write(to: url, options: .atomic)
    }
}
