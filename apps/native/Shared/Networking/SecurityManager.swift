//
//  SecurityManager.swift
//  MedStation
//
//  Minimal security manager for network firewall integration.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "SecurityManager")

// MARK: - Network Decision

enum NetworkDecision: String, Sendable {
    case allowed
    case blocked
    case needsApproval
}

struct NetworkValidationResult: Sendable {
    let allowed: Bool
    let needsApproval: Bool
    let reason: String
}

// MARK: - Security Manager

@MainActor
final class SecurityManager {
    static let shared = SecurityManager()

    var networkFirewallEnabled: Bool = true

    private var approvedDomains: Set<String> = []
    private var blockedDomains: Set<String> = []

    private init() {
        // Always allow localhost for Ollama
        approvedDomains.insert("localhost")
        approvedDomains.insert("127.0.0.1")
    }

    func validateNetworkRequest(_ request: URLRequest) -> NetworkValidationResult {
        guard let host = request.url?.host else {
            return NetworkValidationResult(allowed: false, needsApproval: false, reason: "No host")
        }

        if isLocalhost(host) || approvedDomains.contains(host) {
            return NetworkValidationResult(allowed: true, needsApproval: false, reason: "Approved domain")
        }

        if blockedDomains.contains(host) {
            return NetworkValidationResult(allowed: false, needsApproval: false, reason: "Blocked domain")
        }

        return NetworkValidationResult(allowed: false, needsApproval: true, reason: "Unknown domain")
    }

    nonisolated func isLocalhost(_ host: String) -> Bool {
        host == "localhost" || host == "127.0.0.1" || host == "::1"
    }

    func logNetworkAttempt(_ request: URLRequest, decision: NetworkDecision, reason: String) {
        let url = request.url?.absoluteString ?? "unknown"
        logger.debug("Network \(decision.rawValue): \(url) - \(reason)")
    }

    func approveDomain(_ host: String, permanently: Bool) {
        approvedDomains.insert(host)
        if permanently {
            var saved = UserDefaults.standard.stringArray(forKey: "approvedDomains") ?? []
            saved.append(host)
            UserDefaults.standard.set(saved, forKey: "approvedDomains")
        }
    }

    func blockDomain(_ host: String) {
        blockedDomains.insert(host)
    }

    func setNetworkFirewall(enabled: Bool) {
        networkFirewallEnabled = enabled
        UserDefaults.standard.set(enabled, forKey: "networkFirewallEnabled")
    }
}
