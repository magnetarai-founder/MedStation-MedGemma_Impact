//
//  NetworkFirewallProtocol.swift
//  MagnetarStudio
//
//  Custom URLProtocol that intercepts all network requests and enforces firewall rules
//  Part of Little Snitch-style network firewall implementation
//

import Foundation

/// Custom URLProtocol that intercepts all outgoing network requests
final class NetworkFirewallProtocol: URLProtocol, @unchecked Sendable {

    private var dataTask: URLSessionDataTask?
    private static var internalSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.protocolClasses = [] // Don't intercept internal requests
        return URLSession(configuration: config)
    }()

    // MARK: - URLProtocol Overrides

    override class func canInit(with request: URLRequest) -> Bool {
        // Only intercept HTTP/HTTPS requests
        guard let scheme = request.url?.scheme else { return false }
        guard scheme == "http" || scheme == "https" else { return false }

        // Avoid infinite loops - don't intercept requests we've already processed
        guard property(forKey: "NetworkFirewallHandled", in: request) == nil else {
            return false
        }

        return true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        return request
    }

    override func startLoading() {
        // Mark request as handled to avoid infinite loop
        guard let mutableRequest = (request as NSURLRequest).mutableCopy() as? NSMutableURLRequest else {
            let error = NSError(domain: "com.magnetarstudio.firewall", code: -1,
                                userInfo: [NSLocalizedDescriptionKey: "Failed to create mutable request"])
            client?.urlProtocol(self, didFailWithError: error)
            return
        }
        NetworkFirewallProtocol.setProperty(true, forKey: "NetworkFirewallHandled", in: mutableRequest)

        // Check firewall on main actor
        Task { @MainActor in
            let decision = SecurityManager.shared.validateNetworkRequest(request)

            if decision.needsApproval {
                // Show approval modal and wait for user decision
                await handleApprovalRequired(request: request)
            } else if decision.allowed {
                // Proceed with request
                await proceedWithRequest(mutableRequest as URLRequest)
            } else {
                // Block request
                blockRequest(reason: decision.reason)
            }
        }
    }

    override func stopLoading() {
        dataTask?.cancel()
        dataTask = nil
    }

    // MARK: - Request Handling

    @MainActor
    private func handleApprovalRequired(request: URLRequest) async {
        guard let url = request.url, let _ = url.host else {
            blockRequest(reason: "Invalid URL")
            return
        }

        // Post notification to show approval modal
        let userInfo: [String: Any] = [
            "request": request,
            "protocol": self
        ]

        NotificationCenter.default.post(
            name: .networkApprovalRequired,
            object: nil,
            userInfo: userInfo
        )

        // The approval modal will call approveRequest() or denyRequest() on this protocol instance
    }

    private func proceedWithRequest(_ request: URLRequest) async {
        // Log the allowed request
        await MainActor.run {
            SecurityManager.shared.logNetworkAttempt(
                request,
                decision: .allowed,
                reason: "Firewall approved"
            )
        }

        // Execute the request using internal session (won't be intercepted again)
        dataTask = Self.internalSession.dataTask(with: request) { @Sendable [weak self] data, response, error in
            guard let self = self else { return }

            if let error = error {
                self.client?.urlProtocol(self, didFailWithError: error)
                return
            }

            if let response = response {
                self.client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .allowed)
            }

            if let data = data {
                self.client?.urlProtocol(self, didLoad: data)
            }

            self.client?.urlProtocolDidFinishLoading(self)
        }

        dataTask?.resume()
    }

    private func blockRequest(reason: String) {
        Task { @MainActor in
            SecurityManager.shared.logNetworkAttempt(
                request,
                decision: .blocked,
                reason: reason
            )
        }

        let error = NSError(
            domain: "com.magnetarstudio.firewall",
            code: 403,
            userInfo: [
                NSLocalizedDescriptionKey: "Network request blocked by firewall: \(reason)"
            ]
        )

        client?.urlProtocol(self, didFailWithError: error)
    }

    // MARK: - Public API for Approval Modal

    /// Called by approval modal when user approves request
    func approveRequest(permanently: Bool) {
        guard let url = request.url, let host = url.host else { return }

        Task { @MainActor in
            SecurityManager.shared.approveDomain(host, permanently: permanently)
            await proceedWithRequest(request)
        }
    }

    /// Called by approval modal when user denies request
    func denyRequest(permanently: Bool) {
        guard let url = request.url, let host = url.host else { return }

        Task { @MainActor in
            if permanently {
                SecurityManager.shared.blockDomain(host)
            }
            blockRequest(reason: "User denied")
        }
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let networkApprovalRequired = Notification.Name("NetworkApprovalRequired")
}
