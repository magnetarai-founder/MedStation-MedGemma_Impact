//
//  APIConfiguration.swift
//  MagnetarStudio
//
//  Centralized API configuration with HTTPS enforcement
//

import Foundation

/// Centralized API configuration with security enforcement
final class APIConfiguration {
    static let shared = APIConfiguration()

    /// Base API URL with HTTPS enforcement for non-localhost
    let baseURL: String

    /// Base API URL with version prefix
    var versionedBaseURL: String {
        "\(baseURL)/v1"
    }

    /// Vault service URL
    var vaultURL: String {
        "\(versionedBaseURL)/vault"
    }

    private init() {
        // Read from environment or default to localhost
        // For production/remote: Set API_BASE_URL environment variable to HTTPS endpoint
        if let envBaseURL = ProcessInfo.processInfo.environment["API_BASE_URL"] {
            self.baseURL = envBaseURL
        } else {
            // Local development only - use HTTP for localhost
            self.baseURL = "http://localhost:8000/api"
        }

        // CRITICAL SECURITY: Enforce HTTPS for non-localhost URLs
        if !isLocalhost(baseURL) && baseURL.hasPrefix("http://") {
            print("⚠️ SECURITY ERROR: Non-localhost URL configured with HTTP instead of HTTPS")
            print("⚠️ URL: \(baseURL)")
            assertionFailure("SECURITY: Non-localhost API must use HTTPS")
        }

        print("✅ API Configuration initialized: \(baseURL)")
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
