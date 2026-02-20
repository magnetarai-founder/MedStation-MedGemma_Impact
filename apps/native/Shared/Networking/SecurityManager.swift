//
//  SecurityManager.swift
//  MedStation
//
//  Security settings state for the network firewall UI toggle.
//

import Foundation
import Observation

@MainActor
@Observable
final class SecurityManager {
    static let shared = SecurityManager()

    var networkFirewallEnabled: Bool = true

    private init() {}

    func setNetworkFirewall(enabled: Bool) {
        networkFirewallEnabled = enabled
        UserDefaults.standard.set(enabled, forKey: "networkFirewallEnabled")
    }
}
