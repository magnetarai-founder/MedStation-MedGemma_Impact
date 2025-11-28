//
//  Logger.swift
//  MagnetarStudio
//
//  Centralized logging utility with proper levels and formatting
//

import Foundation
import OSLog

enum Logger {
    private static let subsystem = Bundle.main.bundleIdentifier ?? "com.magnetar.studio"

    // MARK: - Log Categories

    static let auth = OSLog(subsystem: subsystem, category: "Authentication")
    static let database = OSLog(subsystem: subsystem, category: "Database")
    static let chat = OSLog(subsystem: subsystem, category: "Chat")
    static let network = OSLog(subsystem: subsystem, category: "Network")
    static let models = OSLog(subsystem: subsystem, category: "Models")
    static let general = OSLog(subsystem: subsystem, category: "General")

    // MARK: - Logging Methods

    static func info(_ message: String, category: OSLog = .general, file: String = #file, function: String = #function, line: Int = #line) {
        os_log(.info, log: category, "%{public}@", formatMessage(message, file: file, function: function, line: line))
    }

    static func debug(_ message: String, category: OSLog = .general, file: String = #file, function: String = #function, line: Int = #line) {
        #if DEBUG
        os_log(.debug, log: category, "%{public}@", formatMessage(message, file: file, function: function, line: line))
        #endif
    }

    static func error(_ message: String, error: Error? = nil, category: OSLog = .general, file: String = #file, function: String = #function, line: Int = #line) {
        let fullMessage = error != nil ? "\(message): \(error!.localizedDescription)" : message
        os_log(.error, log: category, "%{public}@", formatMessage(fullMessage, file: file, function: function, line: line))
    }

    static func warning(_ message: String, category: OSLog = .general, file: String = #file, function: String = #function, line: Int = #line) {
        os_log(.default, log: category, "[WARNING] %{public}@", formatMessage(message, file: file, function: function, line: line))
    }

    // MARK: - Private Helpers

    private static func formatMessage(_ message: String, file: String, function: String, line: Int) -> String {
        let filename = URL(fileURLWithPath: file).lastPathComponent
        return "[\(filename):\(line)] \(function) - \(message)"
    }
}
