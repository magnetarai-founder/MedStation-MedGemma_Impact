//
//  SecurityManager.swift
//  MagnetarStudio
//
//  Centralized security management for panic mode, network validation, and audit logging
//  Implements security roadmap requirements for persecution-ready deployment
//

import Foundation
import AppKit
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SecurityManager")

/// Centralized security manager (singleton)
@Observable
public final class SecurityManager {
    public static let shared = SecurityManager()

    // MARK: - Observable State

    public private(set) var networkFirewallEnabled: Bool = false
    public private(set) var panicModeActive: Bool = false
    public private(set) var securityEvents: [SecurityEvent] = []

    // MARK: - Private State

    private var approvedDomains: Set<String> = []
    private var blockedDomains: Set<String> = []
    private var pendingRequests: [UUID: URLRequest] = [:]

    private init() {
        // Restore persisted firewall state
        networkFirewallEnabled = UserDefaults.standard.bool(forKey: "networkFirewallEnabled")
        loadFirewallRules()
    }

    // MARK: - Panic Mode

    /// Trigger panic mode with specified level
    func triggerPanicMode(level: PanicLevel, reason: String? = nil) async throws {
        logSecurityEvent(SecurityEvent(
            type: .panicTriggered,
            level: level,
            message: "Panic mode triggered: \(level)",
            details: ["reason": reason ?? "User-initiated"]
        ))

        panicModeActive = true

        switch level {
        case .standard:
            try await triggerStandardPanic(reason: reason)
        case .emergency:
            try await triggerEmergencyPanic(reason: reason)
        }
    }

    private func triggerStandardPanic(reason: String?) async throws {
        let response = try await PanicModeService.shared.triggerPanicMode(
            level: .standard,
            reason: reason
        )

        logSecurityEvent(SecurityEvent(
            type: .panicExecuted,
            level: .standard,
            message: "Standard panic completed",
            details: [
                "actions_taken": response.actionsTaken.joined(separator: ", "),
                "errors": response.errors.joined(separator: ", ")
            ]
        ))
    }

    private func triggerEmergencyPanic(reason: String?) async throws {
        // Delegate to EmergencyModeService for DoD 7-pass wipe + self-uninstall
        // Triple-click detection is handled in HeaderComponents.swift → EmergencyConfirmationModal
        let report = try await EmergencyModeService.shared.triggerEmergency(
            reason: reason,
            confirmationMethod: .panicButton  // Called via SecurityManager
        )

        logSecurityEvent(SecurityEvent(
            type: .panicExecuted,
            level: .emergency,
            message: report.simulated ? "Emergency simulation complete" : "Emergency wipe executed",
            details: [
                "files_wiped": String(report.filesWiped),
                "passes": String(report.passes),
                "duration_seconds": String(format: "%.2f", report.durationSeconds),
                "errors": report.errors.joined(separator: ", "),
                "simulated": String(report.simulated)
            ]
        ))

        if !report.success {
            throw PanicModeError.emergencyModeFailed(errors: report.errors)
        }
    }

    // MARK: - Network Firewall

    /// Enable or disable network firewall
    public func setNetworkFirewall(enabled: Bool) {
        networkFirewallEnabled = enabled
        UserDefaults.standard.set(enabled, forKey: "networkFirewallEnabled")

        logSecurityEvent(SecurityEvent(
            type: .firewallToggled,
            level: .standard,
            message: "Network firewall \(enabled ? "enabled" : "disabled")",
            details: ["enabled": String(enabled)]
        ))
    }

    /// Validate network request against firewall rules
    public func validateNetworkRequest(_ request: URLRequest) -> NetworkDecision {
        guard networkFirewallEnabled else {
            return NetworkDecision(allowed: true, reason: "Firewall disabled")
        }

        guard let url = request.url, let host = url.host else {
            return NetworkDecision(allowed: false, reason: "Invalid URL")
        }

        // Check if domain is blocked
        if blockedDomains.contains(host) {
            logNetworkAttempt(request, decision: .blocked, reason: "Domain blocked")
            return NetworkDecision(allowed: false, reason: "Domain is blocked")
        }

        // Check if domain is approved
        if approvedDomains.contains(host) {
            return NetworkDecision(allowed: true, reason: "Domain pre-approved")
        }

        // Localhost is always allowed for development
        if isLocalhost(host) {
            return NetworkDecision(allowed: true, reason: "Localhost development")
        }

        // Unknown domain - requires user approval
        return NetworkDecision(
            allowed: false,
            reason: "Domain requires approval",
            needsApproval: true
        )
    }

    /// Log network attempt (for audit trail)
    public func logNetworkAttempt(_ request: URLRequest, decision: NetworkOutcome, reason: String) {
        guard let url = request.url else { return }

        logSecurityEvent(SecurityEvent(
            type: .networkAttempt,
            level: .standard,
            message: "Network request: \(decision.rawValue)",
            details: [
                "url": url.absoluteString,
                "method": request.httpMethod ?? "GET",
                "decision": decision.rawValue,
                "reason": reason
            ]
        ))
    }

    /// Approve domain for network access
    public func approveDomain(_ domain: String, permanently: Bool = false) {
        if permanently {
            approvedDomains.insert(domain)
            saveFirewallRules()
        }

        logSecurityEvent(SecurityEvent(
            type: .domainApproved,
            level: .standard,
            message: "Domain approved: \(domain)",
            details: ["permanent": String(permanently)]
        ))
    }

    /// Block domain permanently
    public func blockDomain(_ domain: String) {
        blockedDomains.insert(domain)
        approvedDomains.remove(domain)
        saveFirewallRules()

        logSecurityEvent(SecurityEvent(
            type: .domainBlocked,
            level: .standard,
            message: "Domain blocked: \(domain)",
            details: ["domain": domain]
        ))
    }

    // MARK: - Security Events

    /// Log a security event
    func logSecurityEvent(_ event: SecurityEvent) {
        securityEvents.append(event)

        // Log to unified logger — use debug for routine events, info for important ones
        switch event.type {
        case .networkAttempt:
            logger.debug("[\(event.type.rawValue)] \(event.message)")
        default:
            logger.info("[\(event.type.rawValue)] \(event.message)")
        }

        // Send to backend audit API (non-blocking, skip routine network events)
        if event.type != .networkAttempt {
            Task {
                await sendAuditLog(event)
            }
        }
    }

    /// URLSession that bypasses NetworkFirewallProtocol to prevent recursive interception
    private static let auditSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.protocolClasses = []  // No custom protocols — avoids firewall re-entry
        return URLSession(configuration: config)
    }()

    /// Send security event to backend audit API
    private func sendAuditLog(_ event: SecurityEvent) async {
        // Only send audit logs when authenticated (avoids 401 spam during startup)
        guard let token = KeychainService.shared.loadToken() else {
            return  // Skip remote logging when not authenticated
        }

        do {
            // Build audit log request
            guard let url = URL(string: "\(APIConfiguration.shared.versionedBaseURL)/audit/log") else {
                return
            }
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            // Convert SecurityEvent to backend format
            let auditPayload: [String: Any] = [
                "action": "security.\(event.type.rawValue)",
                "resource_id": event.id.uuidString,
                "details": [
                    "level": event.level.rawValue,
                    "message": event.message,
                    "timestamp": ISO8601DateFormatter().string(from: event.timestamp),
                    "event_details": event.details
                ]
            ]
            request.httpBody = try JSONSerialization.data(withJSONObject: auditPayload)

            // Use audit-specific session that bypasses the firewall protocol
            let (_, response) = try await Self.auditSession.data(for: request)

            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 201 {
                logger.debug("Audit log response: \(httpResponse.statusCode)")
            }
        } catch {
            logger.debug("Audit log send failed: \(error.localizedDescription)")
        }
    }

    /// Get recent security events
    func getSecurityEvents(limit: Int = 100) -> [SecurityEvent] {
        return Array(securityEvents.suffix(limit))
    }

    /// Clear security events (admin only)
    func clearSecurityEvents() {
        securityEvents.removeAll()
    }

    // MARK: - Private Helpers

    func isLocalhost(_ host: String) -> Bool {
        return host == "localhost" ||
               host == "127.0.0.1" ||
               host == "::1" ||
               host.hasSuffix(".local")
    }

    // Keychain keys for firewall rules (security-sensitive data)
    private let approvedDomainsKey = "firewall_approved_domains"
    private let blockedDomainsKey = "firewall_blocked_domains"

    private func loadFirewallRules() {
        // Load from Keychain (secure storage for security-critical firewall rules)
        // Domain lists are stored as JSON strings

        if let approvedJson = KeychainService.shared.loadToken(forKey: approvedDomainsKey),
           let data = approvedJson.data(using: .utf8) {
            do {
                approvedDomains = Set(try JSONDecoder().decode([String].self, from: data))
            } catch {
                logger.warning("[Security] Failed to decode approved domains: \(error)")
            }
        }

        if let blockedJson = KeychainService.shared.loadToken(forKey: blockedDomainsKey),
           let data = blockedJson.data(using: .utf8) {
            do {
                blockedDomains = Set(try JSONDecoder().decode([String].self, from: data))
            } catch {
                logger.warning("[Security] Failed to decode blocked domains: \(error)")
            }
        }

        // Migration: If data exists in UserDefaults but not Keychain, migrate it
        if approvedDomains.isEmpty,
           let oldApproved = UserDefaults.standard.array(forKey: "ApprovedDomains") as? [String],
           !oldApproved.isEmpty {
            approvedDomains = Set(oldApproved)
            saveFirewallRules()
            // Clean up old UserDefaults storage after migration
            UserDefaults.standard.removeObject(forKey: "ApprovedDomains")
        }

        if blockedDomains.isEmpty,
           let oldBlocked = UserDefaults.standard.array(forKey: "BlockedDomains") as? [String],
           !oldBlocked.isEmpty {
            blockedDomains = Set(oldBlocked)
            saveFirewallRules()
            // Clean up old UserDefaults storage after migration
            UserDefaults.standard.removeObject(forKey: "BlockedDomains")
        }
    }

    private func saveFirewallRules() {
        // Save to Keychain as JSON strings (secure storage)
        do {
            let approvedJson = try JSONEncoder().encode(Array(approvedDomains))
            if let jsonString = String(data: approvedJson, encoding: .utf8) {
                try KeychainService.shared.saveToken(jsonString, forKey: approvedDomainsKey)
            }

            let blockedJson = try JSONEncoder().encode(Array(blockedDomains))
            if let jsonString = String(data: blockedJson, encoding: .utf8) {
                try KeychainService.shared.saveToken(jsonString, forKey: blockedDomainsKey)
            }
        } catch {
            logger.warning("Failed to save firewall rules to Keychain: \(error)")
        }
    }
}

// MARK: - Supporting Types

public struct NetworkDecision {
    let allowed: Bool
    let reason: String
    var needsApproval: Bool = false
}

public enum NetworkOutcome: String {
    case allowed = "allowed"
    case blocked = "blocked"
    case pending = "pending_approval"
}

public struct SecurityEvent: Identifiable, Codable, Sendable {
    public let id: UUID
    public let timestamp: Date
    public let type: SecurityEventType
    public let level: PanicLevel
    public let message: String
    public let details: [String: String]

    public init(id: UUID = UUID(),
         timestamp: Date = Date(),
         type: SecurityEventType,
         level: PanicLevel,
         message: String,
         details: [String: String] = [:]) {
        self.id = id
        self.timestamp = timestamp
        self.type = type
        self.level = level
        self.message = message
        self.details = details
    }
}

public enum SecurityEventType: String, Codable, Sendable {
    case panicTriggered = "panic_triggered"
    case panicExecuted = "panic_executed"
    case firewallToggled = "firewall_toggled"
    case networkAttempt = "network_attempt"
    case domainApproved = "domain_approved"
    case domainBlocked = "domain_blocked"
    case vaultUnlocked = "vault_unlocked"
    case vaultLocked = "vault_locked"
    case authSuccess = "auth_success"
    case authFailure = "auth_failure"
}
