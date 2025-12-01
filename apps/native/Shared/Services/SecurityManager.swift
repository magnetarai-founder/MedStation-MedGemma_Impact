//
//  SecurityManager.swift
//  MagnetarStudio
//
//  Centralized security management for panic mode, network validation, and audit logging
//  Implements security roadmap requirements for persecution-ready deployment
//

import Foundation
import AppKit

/// Centralized security manager (singleton)
@MainActor
final class SecurityManager: ObservableObject {
    static let shared = SecurityManager()

    // MARK: - Published State

    @Published private(set) var networkFirewallEnabled: Bool = false
    @Published private(set) var panicModeActive: Bool = false
    @Published private(set) var securityEvents: [SecurityEvent] = []

    // MARK: - Private State

    private var approvedDomains: Set<String> = []
    private var blockedDomains: Set<String> = []
    private var pendingRequests: [UUID: URLRequest] = [:]

    private init() {
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
        // TODO: Implement emergency mode (triple-click, DoD wipe, self-uninstall)
        logSecurityEvent(SecurityEvent(
            type: .panicExecuted,
            level: .emergency,
            message: "Emergency mode not yet implemented",
            details: ["status": "pending_implementation"]
        ))

        throw PanicModeError.emergencyModeNotImplemented
    }

    // MARK: - Network Firewall

    /// Enable or disable network firewall
    func setNetworkFirewall(enabled: Bool) {
        networkFirewallEnabled = enabled

        logSecurityEvent(SecurityEvent(
            type: .firewallToggled,
            level: .standard,
            message: "Network firewall \(enabled ? "enabled" : "disabled")",
            details: ["enabled": String(enabled)]
        ))
    }

    /// Validate network request against firewall rules
    func validateNetworkRequest(_ request: URLRequest) -> NetworkDecision {
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
    func logNetworkAttempt(_ request: URLRequest, decision: NetworkOutcome, reason: String) {
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
    func approveDomain(_ domain: String, permanently: Bool = false) {
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
    func blockDomain(_ domain: String) {
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

        // Print to console for debugging
        print("🔒 [\(event.type.rawValue)] \(event.message)")

        // TODO: Send to backend audit API
        Task {
            // await sendAuditLog(event)
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

    private func isLocalhost(_ host: String) -> Bool {
        return host == "localhost" ||
               host == "127.0.0.1" ||
               host == "::1" ||
               host.hasSuffix(".local")
    }

    private func loadFirewallRules() {
        // Load from UserDefaults
        if let approved = UserDefaults.standard.array(forKey: "ApprovedDomains") as? [String] {
            approvedDomains = Set(approved)
        }

        if let blocked = UserDefaults.standard.array(forKey: "BlockedDomains") as? [String] {
            blockedDomains = Set(blocked)
        }
    }

    private func saveFirewallRules() {
        UserDefaults.standard.set(Array(approvedDomains), forKey: "ApprovedDomains")
        UserDefaults.standard.set(Array(blockedDomains), forKey: "BlockedDomains")
    }
}

// MARK: - Supporting Types

struct NetworkDecision {
    let allowed: Bool
    let reason: String
    var needsApproval: Bool = false
}

enum NetworkOutcome: String {
    case allowed = "allowed"
    case blocked = "blocked"
    case pending = "pending_approval"
}

struct SecurityEvent: Identifiable, Codable {
    let id: UUID
    let timestamp: Date
    let type: SecurityEventType
    let level: PanicLevel
    let message: String
    let details: [String: String]

    init(id: UUID = UUID(),
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

enum SecurityEventType: String, Codable {
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
