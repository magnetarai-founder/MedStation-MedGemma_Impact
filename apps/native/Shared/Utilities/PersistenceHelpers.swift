//
//  PersistenceHelpers.swift
//  MedStation
//
//  Shared save/load utilities that replace the try?-on-persistence anti-pattern.
//  All operations log errors instead of silently swallowing them.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "Persistence")

enum PersistenceHelpers {

    /// Encode and write atomically, logging any failure.
    static func save<T: Encodable>(_ value: T, to url: URL, label: String) {
        do {
            let data = try JSONEncoder().encode(value)
            try data.write(to: url, options: .atomic)
        } catch {
            logger.error("Failed to save \(label): \(error.localizedDescription)")
        }
    }

    /// Encode and write atomically, throwing on failure for callers that need error visibility.
    static func trySave<T: Encodable>(_ value: T, to url: URL, label: String) throws {
        let data = try JSONEncoder().encode(value)
        try data.write(to: url, options: .atomic)
    }

    /// Decode from file, returning nil with log on failure.
    static func load<T: Decodable>(_ type: T.Type, from url: URL, label: String) -> T? {
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(type, from: data)
        } catch {
            logger.error("Failed to load \(label) from \(url.lastPathComponent): \(error.localizedDescription)")
            return nil
        }
    }

    /// Ensure directory exists, logging failure.
    static func ensureDirectory(at url: URL, label: String) {
        do {
            try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        } catch {
            logger.error("Failed to create directory for \(label): \(error.localizedDescription)")
        }
    }

    /// Remove file, logging failure.
    static func remove(at url: URL, label: String) {
        do {
            try FileManager.default.removeItem(at: url)
        } catch {
            logger.error("Failed to remove \(label) at \(url.lastPathComponent): \(error.localizedDescription)")
        }
    }
}
