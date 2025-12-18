//
//  TrustWorkspace.swift
//  MagnetarStudio (macOS)
//
//  MagnetarTrust - Trust Network Workspace
//  Part of MagnetarMission: Decentralized trust for churches, missions, and humanitarian teams
//
//  Phase 1 MVP: Node registration, trust relationships, network visualization
//

import SwiftUI

// MARK: - Trust View Enum

enum TrustView {
    case network      // My trust network visualization
    case nodes        // Browse all nodes (churches, missions, etc.)
    case register     // Register new node
}

// MARK: - Trust Workspace

struct TrustWorkspace: View {
    @State private var currentView: TrustView = .network
    @State private var nodes: [TrustNode] = []
    @State private var trustNetwork: TrustNetworkResponse? = nil
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    // Modals
    @State private var showRegisterNode = false
    @State private var showVouchModal = false
    @State private var selectedNode: TrustNode? = nil

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.05))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content area
            contentArea
        }
        .sheet(isPresented: $showRegisterNode) {
            RegisterNodeModal(onRegister: { node in
                Task {
                    await loadTrustNetwork()
                    await loadNodes()
                }
            })
        }
        .sheet(isPresented: $showVouchModal) {
            if let node = selectedNode {
                VouchNodeModal(node: node, onVouched: {
                    Task {
                        await loadTrustNetwork()
                    }
                })
            }
        }
        .task {
            await loadInitialData()
        }
    }

    // MARK: - Data Loading

    private func loadInitialData() async {
        await loadTrustNetwork()
        await loadNodes()
    }

    private func loadTrustNetwork() async {
        isLoading = true
        defer { isLoading = false }

        do {
            trustNetwork = try await TrustService.shared.getTrustNetwork()
            errorMessage = nil
        } catch {
            errorMessage = "Failed to load trust network: \(error.localizedDescription)"
            print("❌ \(errorMessage ?? "")")
        }
    }

    private func loadNodes() async {
        do {
            let response = try await TrustService.shared.listNodes()
            nodes = response.nodes
        } catch {
            print("❌ Failed to load nodes: \(error.localizedDescription)")
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Left: MagnetarTrust title
            HStack(spacing: 8) {
                Image(systemName: "network")
                    .font(.system(size: 18))
                    .foregroundColor(.magnetarPrimary)
                Text("MagnetarTrust")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(.primary)
            }

            Spacer()

            // View tabs
            HStack(spacing: 4) {
                viewTab(title: "Network", icon: "point.3.connected.trianglepath.dotted", view: .network)
                viewTab(title: "Nodes", icon: "person.3", view: .nodes)
                viewTab(title: "Register", icon: "plus.circle", view: .register)
            }

            Spacer()

            // Right: Register Node button
            Button {
                showRegisterNode = true
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "person.badge.plus")
                    Text("Register Node")
                }
                .font(.system(size: 13))
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.magnetarPrimary)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
            .buttonStyle(.plain)
            .help("Register a new trust node")
        }
    }

    private func viewTab(title: String, icon: String, view: TrustView) -> some View {
        Button {
            currentView = view
        } label: {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                Text(title)
                    .font(.system(size: 13))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(currentView == view ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
            )
            .foregroundColor(currentView == view ? .magnetarPrimary : .secondary)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        if isLoading && trustNetwork == nil {
            loadingView
        } else if let error = errorMessage {
            errorView(error)
        } else {
            switch currentView {
            case .network:
                networkView
            case .nodes:
                nodesView
            case .register:
                registerView
            }
        }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Loading trust network...")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)
            Text(message)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") {
                Task {
                    await loadInitialData()
                }
            }
            .buttonStyle(.bordered)
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Network View

    private var networkView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                if let network = trustNetwork {
                    // Stats
                    HStack(spacing: 32) {
                        statCard(title: "Direct Trusts", value: "\(network.directTrusts.count)", icon: "person.2")
                        statCard(title: "Vouched", value: "\(network.vouchedTrusts.count)", icon: "hand.thumbsup")
                        statCard(title: "Network", value: "\(network.networkTrusts.count)", icon: "point.3.connected.trianglepath.dotted")
                        statCard(title: "Total", value: "\(network.totalNetworkSize)", icon: "network")
                    }
                    .padding(.bottom, 8)

                    // Trust levels
                    trustLevelSection(title: "Direct Trusts", nodes: network.directTrusts, color: .green)
                    trustLevelSection(title: "Vouched Trusts", nodes: network.vouchedTrusts, color: .blue)
                    trustLevelSection(title: "Network Trusts", nodes: network.networkTrusts, color: .purple)
                } else {
                    emptyStateView(
                        icon: "network",
                        title: "No Trust Network",
                        message: "Register a node to start building your trust network."
                    )
                }
            }
            .padding(24)
        }
    }

    private func statCard(title: String, value: String, icon: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
                Text(title)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }
            Text(value)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.gray.opacity(0.08))
        )
    }

    private func trustLevelSection(title: String, nodes: [TrustNode], color: Color) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(title)
                    .font(.system(size: 16, weight: .semibold))
                Text("(\(nodes.count))")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            if nodes.isEmpty {
                Text("No \(title.lowercased()) yet")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
                    .padding(.vertical, 12)
            } else {
                VStack(spacing: 8) {
                    ForEach(nodes) { node in
                        nodeRow(node: node, accentColor: color)
                    }
                }
            }
        }
    }

    // MARK: - Nodes View

    private var nodesView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if nodes.isEmpty {
                    emptyStateView(
                        icon: "person.3",
                        title: "No Nodes",
                        message: "Be the first to register a node in the trust network."
                    )
                } else {
                    ForEach(nodes) { node in
                        nodeRow(node: node, accentColor: nodeTypeColor(node.type))
                            .onTapGesture {
                                selectedNode = node
                                showVouchModal = true
                            }
                    }
                }
            }
            .padding(24)
        }
    }

    private func nodeRow(node: TrustNode, accentColor: Color) -> some View {
        HStack(spacing: 12) {
            // Icon
            Image(systemName: nodeTypeIcon(node.type))
                .font(.system(size: 20))
                .foregroundColor(accentColor)
                .frame(width: 40, height: 40)
                .background(
                    Circle()
                        .fill(accentColor.opacity(0.15))
                )

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(node.displayMode == .peacetime ? node.publicName : (node.alias ?? "Anonymous"))
                    .font(.system(size: 14, weight: .medium))
                HStack(spacing: 8) {
                    Text(node.type.rawValue.capitalized)
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                    if let location = node.location, node.displayMode == .peacetime {
                        Text("•")
                            .foregroundColor(.secondary)
                        Text(location)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Hub badge
            if node.isHub {
                Text("HUB")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(Color.orange.opacity(0.2))
                    )
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.gray.opacity(0.06))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(accentColor.opacity(0.2), lineWidth: 1)
        )
    }

    // MARK: - Register View

    private var registerView: some View {
        ScrollView {
            VStack(spacing: 20) {
                Image(systemName: "person.badge.plus")
                    .font(.system(size: 64))
                    .foregroundColor(.magnetarPrimary)

                Text("Register Trust Node")
                    .font(.system(size: 24, weight: .bold))

                Text("Create a new node in the MagnetarTrust network. Nodes can be individuals, churches, missions, families, or organizations.")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 500)

                Button {
                    showRegisterNode = true
                } label: {
                    Text("Register New Node")
                        .font(.system(size: 14, weight: .medium))
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                        .background(Color.magnetarPrimary)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .buttonStyle(.plain)
                .padding(.top, 16)
            }
            .padding(48)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Helper Views

    private func emptyStateView(icon: String, title: String, message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 64))
                .foregroundColor(.secondary.opacity(0.5))
            Text(title)
                .font(.system(size: 20, weight: .semibold))
            Text(message)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(48)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Helpers

    private func nodeTypeIcon(_ type: NodeType) -> String {
        switch type {
        case .individual: return "person"
        case .church: return "building.columns"
        case .mission: return "globe"
        case .family: return "person.3"
        case .organization: return "building.2"
        }
    }

    private func nodeTypeColor(_ type: NodeType) -> Color {
        switch type {
        case .individual: return .blue
        case .church: return .purple
        case .mission: return .green
        case .family: return .orange
        case .organization: return .cyan
        }
    }
}

// MARK: - Placeholder Modals

struct RegisterNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let onRegister: (TrustNode) -> Void

    var body: some View {
        VStack(spacing: 20) {
            Text("Register Node")
                .font(.system(size: 20, weight: .bold))
            Text("Node registration UI coming soon...")
                .foregroundColor(.secondary)
            Button("Close") {
                dismiss()
            }
            .buttonStyle(.bordered)
        }
        .padding(32)
        .frame(width: 400, height: 300)
    }
}

struct VouchNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let node: TrustNode
    let onVouched: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Text("Vouch for \(node.publicName)")
                .font(.system(size: 20, weight: .bold))
            Text("Vouching UI coming soon...")
                .foregroundColor(.secondary)
            Button("Close") {
                dismiss()
            }
            .buttonStyle(.bordered)
        }
        .padding(32)
        .frame(width: 400, height: 300)
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    TrustWorkspace()
}
#endif
