//
//  PluginRegistry.swift
//  MagnetarStudio
//
//  Central registry for all plugin extension points.
//  Plugins register handlers; the app queries registered extensions at runtime.
//

import Foundation
import SwiftUI

// MARK: - Extension Point Protocols

/// A custom export format handler provided by a plugin.
protocol PluginExportHandler: Sendable {
    var formatName: String { get }
    var fileExtension: String { get }
    func export(content: String, title: String) async throws -> Data
}

/// A custom automation action handler provided by a plugin.
protocol PluginAutomationHandler: Sendable {
    var actionName: String { get }
    var icon: String { get }
    func execute(parameters: [String: String], context: [String: String]) async throws
}

/// A custom chart type handler provided by a plugin.
protocol PluginChartHandler: Sendable {
    var chartName: String { get }
    var icon: String { get }
}

// MARK: - Registry Entry Types

/// Registered export format entry.
struct RegisteredExportFormat: Identifiable, Sendable {
    let id: String
    let pluginId: String
    let handler: any PluginExportHandler
}

/// Registered automation action entry.
struct RegisteredAutomationAction: Identifiable, Sendable {
    let id: String
    let pluginId: String
    let handler: any PluginAutomationHandler
}

/// Registered chart type entry.
struct RegisteredChartType: Identifiable, Sendable {
    let id: String
    let pluginId: String
    let handler: any PluginChartHandler
}

/// Registered AI strategy entry.
struct RegisteredAIStrategy: Identifiable, Sendable {
    let id: String
    let pluginId: String
    let strategy: any WorkspaceAIStrategy
}

// MARK: - Plugin Registry

/// Central registry for all plugin extension points.
/// Thread-safe via @MainActor isolation.
@MainActor
final class PluginRegistry {
    static let shared = PluginRegistry()

    // MARK: - Registered Extensions

    private(set) var exportFormats: [RegisteredExportFormat] = []
    private(set) var automationActions: [RegisteredAutomationAction] = []
    private(set) var chartTypes: [RegisteredChartType] = []
    private(set) var aiStrategies: [RegisteredAIStrategy] = []

    private init() {}

    // MARK: - Registration

    func register(exportFormat handler: any PluginExportHandler, pluginId: String) {
        let id = "\(pluginId).\(handler.formatName)"
        guard !exportFormats.contains(where: { $0.id == id }) else { return }
        exportFormats.append(RegisteredExportFormat(id: id, pluginId: pluginId, handler: handler))
    }

    func register(automationAction handler: any PluginAutomationHandler, pluginId: String) {
        let id = "\(pluginId).\(handler.actionName)"
        guard !automationActions.contains(where: { $0.id == id }) else { return }
        automationActions.append(RegisteredAutomationAction(id: id, pluginId: pluginId, handler: handler))
    }

    func register(chartType handler: any PluginChartHandler, pluginId: String) {
        let id = "\(pluginId).\(handler.chartName)"
        guard !chartTypes.contains(where: { $0.id == id }) else { return }
        chartTypes.append(RegisteredChartType(id: id, pluginId: pluginId, handler: handler))
    }

    func register(aiStrategy strategy: any WorkspaceAIStrategy, pluginId: String) {
        let id = "\(pluginId).ai"
        guard !aiStrategies.contains(where: { $0.id == id }) else { return }
        aiStrategies.append(RegisteredAIStrategy(id: id, pluginId: pluginId, strategy: strategy))
    }

    // MARK: - Unregistration

    func unregisterAll(pluginId: String) {
        exportFormats.removeAll { $0.pluginId == pluginId }
        automationActions.removeAll { $0.pluginId == pluginId }
        chartTypes.removeAll { $0.pluginId == pluginId }
        aiStrategies.removeAll { $0.pluginId == pluginId }
    }

    // MARK: - Lookup

    func exportHandler(for formatId: String) -> (any PluginExportHandler)? {
        exportFormats.first { $0.id == formatId }?.handler
    }

    func automationHandler(for actionId: String) -> (any PluginAutomationHandler)? {
        automationActions.first { $0.id == actionId }?.handler
    }

    // MARK: - Stats

    var totalRegistrations: Int {
        exportFormats.count + automationActions.count + chartTypes.count + aiStrategies.count
    }

    func registrations(for pluginId: String) -> Int {
        exportFormats.filter { $0.pluginId == pluginId }.count +
        automationActions.filter { $0.pluginId == pluginId }.count +
        chartTypes.filter { $0.pluginId == pluginId }.count +
        aiStrategies.filter { $0.pluginId == pluginId }.count
    }
}
