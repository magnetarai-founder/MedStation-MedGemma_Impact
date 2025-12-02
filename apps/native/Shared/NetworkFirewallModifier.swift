//
//  NetworkFirewallModifier.swift
//  MagnetarStudio
//
//  View modifier that listens for network approval requests and displays modal
//

import SwiftUI
import Combine

struct NetworkFirewallModifier: ViewModifier {
    @State private var showApprovalModal = false
    @State private var pendingRequest: URLRequest?
    @State private var pendingProtocol: NetworkFirewallProtocol?
    @State private var cancellable: AnyCancellable?

    func body(content: Content) -> some View {
        content
            .onAppear {
                startListening()
            }
            .onDisappear {
                cancellable?.cancel()
            }
            .sheet(isPresented: $showApprovalModal) {
                if let request = pendingRequest {
                    NetworkApprovalModal(
                        request: request,
                        onApprove: { permanently in
                            pendingProtocol?.approveRequest(permanently: permanently)
                            clearPending()
                        },
                        onDeny: { permanently in
                            pendingProtocol?.denyRequest(permanently: permanently)
                            clearPending()
                        }
                    )
                }
            }
    }

    private func startListening() {
        cancellable = NotificationCenter.default.publisher(for: .networkApprovalRequired)
            .receive(on: DispatchQueue.main)
            .sink { notification in
                guard let userInfo = notification.userInfo,
                      let request = userInfo["request"] as? URLRequest,
                      let proto = userInfo["protocol"] as? NetworkFirewallProtocol else {
                    return
                }

                pendingRequest = request
                pendingProtocol = proto
                showApprovalModal = true
            }
    }

    private func clearPending() {
        pendingRequest = nil
        pendingProtocol = nil
        showApprovalModal = false
    }
}

extension View {
    /// Adds network firewall approval modal support to the view
    func withNetworkFirewall() -> some View {
        modifier(NetworkFirewallModifier())
    }
}
