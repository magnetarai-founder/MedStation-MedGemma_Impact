//
//  APIConfiguration.swift
//  MagnetarStudio
//
//  Centralized API configuration with HTTPS enforcement
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "APIConfiguration")

/// Centralized API configuration with security enforcement
final class APIConfiguration {
    static let shared = APIConfiguration()

    /// Base API URL with HTTPS enforcement for non-localhost
    /// Priority: env var > UserDefaults (Settings UI) > default localhost
    var baseURL: String {
        if let envURL = ProcessInfo.processInfo.environment["API_BASE_URL"] {
            return envURL
        }
        if let userURL = UserDefaults.standard.string(forKey: "apiBaseURL"),
           !userURL.isEmpty,
           userURL != _defaultBaseURL {
            return userURL
        }
        return _defaultBaseURL
    }

    private let _defaultBaseURL: String = "http://localhost:8000/api"

    /// Ollama server URL (local LLM inference)
    let ollamaURL: String

    /// Base API URL with version prefix
    var versionedBaseURL: String {
        "\(baseURL)/v1"
    }

    /// Vault service URL
    var vaultURL: String {
        "\(versionedBaseURL)/vault"
    }

    /// Chat models endpoint
    var chatModelsURL: String {
        "\(versionedBaseURL)/chat/models"
    }

    /// Health check endpoint (at root, not versioned)
    var healthURL: String {
        // Health is at /health, not /api/v1/health
        let rootURL = baseURL.replacingOccurrences(of: "/api", with: "")
        return "\(rootURL)/health"
    }

    /// Context Engine status endpoint
    var contextStatusURL: String {
        "\(versionedBaseURL)/context/status"
    }

    /// Context semantic search endpoint
    var contextSearchURL: String {
        "\(versionedBaseURL)/context/search"
    }

    /// Vault semantic search endpoint
    var vaultSearchURL: String {
        "\(versionedBaseURL)/vault/search/semantic"
    }

    /// Data/Query semantic search endpoint
    var dataSearchURL: String {
        "\(versionedBaseURL)/data/search/semantic"
    }

    // MARK: - Cloud Sync (MagnetarCloud)

    /// Cloud OAuth base URL
    var cloudOAuthURL: String {
        "\(versionedBaseURL)/cloud/oauth"
    }

    /// Cloud sync base URL
    var cloudSyncURL: String {
        "\(versionedBaseURL)/cloud/sync"
    }

    /// Cloud sync status endpoint
    var cloudSyncStatusURL: String {
        "\(cloudSyncURL)/status"
    }

    /// Cloud storage base URL
    var cloudStorageURL: String {
        "\(versionedBaseURL)/cloud/storage"
    }

    private init() {
        // Ollama URL (always local, no remote option)
        if let envOllamaURL = ProcessInfo.processInfo.environment["OLLAMA_URL"] {
            self.ollamaURL = envOllamaURL
        } else {
            self.ollamaURL = "http://localhost:11434"
        }

        // CRITICAL SECURITY: Enforce HTTPS for non-localhost URLs
        let resolved = baseURL
        if !isLocalhost(resolved) && resolved.hasPrefix("http://") {
            logger.critical("SECURITY ERROR: Non-localhost URL configured with HTTP instead of HTTPS")
            logger.critical("URL: \(resolved)")
            assertionFailure("SECURITY: Non-localhost API must use HTTPS")
        }

        logger.info("API Configuration initialized: \(resolved)")
    }

    /// Check if URL is localhost or loopback
    private func isLocalhost(_ url: String) -> Bool {
        return url.contains("localhost") ||
               url.contains("127.0.0.1") ||
               url.contains("::1")
    }

    /// Validate that a URL uses HTTPS or is localhost
    func validateURL(_ urlString: String) -> Bool {
        if isLocalhost(urlString) {
            return true // Localhost can use HTTP for development
        }
        return urlString.hasPrefix("https://")
    }
}
