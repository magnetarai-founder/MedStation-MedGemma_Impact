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
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TrustWorkspace")

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
    @State private var needsRegistration: Bool = false  // User hasn't registered yet

    // Modals
    @State private var showRegisterNode = false
    @State private var showVouchModal = false
    @State private var showSafetyNumberModal = false
    @State private var selectedNode: TrustNode? = nil

    // Search
    @State private var searchText: String = ""

    var filteredNodes: [TrustNode] {
        if searchText.isEmpty {
            return nodes
        }
        return nodes.filter {
            $0.publicName.localizedCaseInsensitiveContains(searchText) ||
            $0.type.rawValue.localizedCaseInsensitiveContains(searchText) ||
            ($0.alias ?? "").localizedCaseInsensitiveContains(searchText) ||
            ($0.location ?? "").localizedCaseInsensitiveContains(searchText)
        }
    }

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
        .sheet(isPresented: $showSafetyNumberModal) {
            if let node = selectedNode {
                SafetyNumberVerificationModal(node: node, onVerified: {
                    // Verification successful
                    logger.info("Verified safety number for \(node.publicName)")
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
            needsRegistration = false
        } catch let error as ApiError {
            // Check if this is a "not registered" 404 error
            if case .httpError(404, let data) = error,
               let message = String(data: data, encoding: .utf8),
               message.lowercased().contains("not found") || message.lowercased().contains("register") {
                // User needs to register - this is expected for new users
                needsRegistration = true
                errorMessage = nil
                logger.info("User not registered in trust network yet")
            } else {
                errorMessage = "Failed to load trust network: \(error.localizedDescription)"
                logger.error("\(errorMessage ?? "")")
            }
        } catch {
            errorMessage = "Failed to load trust network: \(error.localizedDescription)"
            logger.error("\(errorMessage ?? "")")
        }
    }

    private func loadNodes() async {
        do {
            let response = try await TrustService.shared.listNodes()
            nodes = response.nodes
        } catch {
            logger.error("Failed to load nodes: \(error.localizedDescription)")
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

                // Node count badge
                if !nodes.isEmpty {
                    Text("\(nodes.count)")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.magnetarPrimary.opacity(0.8))
                        .clipShape(Capsule())
                }
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
        if isLoading && trustNetwork == nil && !needsRegistration {
            loadingView
        } else if needsRegistration {
            welcomeView
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

    // MARK: - Welcome View (for unregistered users)

    private var welcomeView: some View {
        VStack(spacing: 24) {
            Image(systemName: "network.badge.shield.half.filled")
                .font(.system(size: 72))
                .foregroundColor(.magnetarPrimary)

            Text("Welcome to MagnetarTrust")
                .font(.system(size: 28, weight: .bold))

            Text("Join the decentralized trust network for churches, missions, families, and humanitarian teams.")
                .font(.system(size: 16))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 500)

            VStack(alignment: .leading, spacing: 12) {
                featureRow(icon: "checkmark.shield", text: "Verify identities through trusted connections")
                featureRow(icon: "person.3", text: "Build trust relationships with churches and missions")
                featureRow(icon: "lock.shield", text: "Persecution-ready with underground mode")
                featureRow(icon: "globe", text: "Connect with the global humanitarian network")
            }
            .padding(.vertical, 16)

            Button {
                showRegisterNode = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "person.badge.plus")
                    Text("Register Your Node")
                }
                .font(.system(size: 16, weight: .semibold))
                .padding(.horizontal, 32)
                .padding(.vertical, 14)
                .background(Color.magnetarPrimary)
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .buttonStyle(.plain)
        }
        .padding(48)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func featureRow(icon: String, text: String) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(.magnetarPrimary)
                .frame(width: 28)
            Text(text)
                .font(.system(size: 14))
                .foregroundColor(.primary)
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
                    HStack(spacing: 16) {
                        statCard(title: "Direct Trusts", value: "\(network.directTrusts.count)", icon: "person.2", color: .green)
                        statCard(title: "Vouched", value: "\(network.vouchedTrusts.count)", icon: "hand.thumbsup", color: .blue)
                        statCard(title: "Network", value: "\(network.networkTrusts.count)", icon: "point.3.connected.trianglepath.dotted", color: .purple)
                        statCard(title: "Total", value: "\(network.totalNetworkSize)", icon: "network", color: .magnetarPrimary)
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

    private func statCard(title: String, value: String, icon: String, color: Color = .magnetarPrimary) -> some View {
        TrustStatCard(title: title, value: value, icon: icon, color: color)
    }

    private func trustLevelSection(title: String, nodes: [TrustNode], color: Color) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Circle()
                    .fill(color)
                    .frame(width: 8, height: 8)
                Text(title)
                    .font(.system(size: 16, weight: .semibold))
                Text("\(nodes.count)")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(color)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(color.opacity(0.1))
                    .clipShape(Capsule())
            }

            if nodes.isEmpty {
                HStack(spacing: 8) {
                    Image(systemName: "person.crop.circle.badge.questionmark")
                        .font(.system(size: 16))
                        .foregroundStyle(.tertiary)
                    Text("No \(title.lowercased()) yet")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                .padding(.vertical, 12)
                .padding(.horizontal, 8)
            } else {
                VStack(spacing: 8) {
                    ForEach(nodes) { node in
                        TrustNodeRow(
                            node: node,
                            accentColor: color,
                            onTap: {
                                selectedNode = node
                                showVouchModal = true
                            },
                            onVerify: {
                                selectedNode = node
                                showSafetyNumberModal = true
                            },
                            onCopyKey: {
                                #if os(macOS)
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(node.publicKey, forType: .string)
                                #endif
                            }
                        )
                    }
                }
            }
        }
    }

    // MARK: - Nodes View

    private var nodesView: some View {
        VStack(spacing: 0) {
            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                TextField("Search nodes...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13))
                if !searchText.isEmpty {
                    Button(action: { searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.gray.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal, 24)
            .padding(.top, 16)
            .padding(.bottom, 8)

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if nodes.isEmpty {
                        emptyStateView(
                            icon: "person.3",
                            title: "No Nodes",
                            message: "Be the first to register a node in the trust network."
                        )
                    } else if filteredNodes.isEmpty {
                        emptyStateView(
                            icon: "magnifyingglass",
                            title: "No Matches",
                            message: "No nodes match your search."
                        )
                    } else {
                        // Node count summary
                        HStack(spacing: 12) {
                            Text("\(filteredNodes.count) nodes")
                                .font(.system(size: 12, weight: .medium))
                                .foregroundStyle(.secondary)

                            Spacer()

                            // Hub count
                            let hubCount = filteredNodes.filter { $0.isHub }.count
                            if hubCount > 0 {
                                HStack(spacing: 4) {
                                    Image(systemName: "star.fill")
                                        .font(.system(size: 10))
                                    Text("\(hubCount) hubs")
                                        .font(.system(size: 10, weight: .medium))
                                }
                                .foregroundStyle(.orange)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.orange.opacity(0.1))
                                .clipShape(Capsule())
                            }
                        }

                        ForEach(filteredNodes) { node in
                            TrustNodeRow(
                                node: node,
                                accentColor: nodeTypeColor(node.type),
                                onTap: {
                                    selectedNode = node
                                    showVouchModal = true
                                },
                                onVerify: {
                                    selectedNode = node
                                    showSafetyNumberModal = true
                                },
                                onCopyKey: {
                                    #if os(macOS)
                                    NSPasteboard.general.clearContents()
                                    NSPasteboard.general.setString(node.publicKey, forType: .string)
                                    #endif
                                }
                            )
                        }
                    }
                }
                .padding(24)
            }
        }
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

// MARK: - Trust Stat Card (with hover effects)

struct TrustStatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(isHovered ? color : .secondary)
                Text(title)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }
            Text(value)
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(isHovered ? color : .primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(isHovered ? color.opacity(0.1) : Color.gray.opacity(0.08))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isHovered ? color.opacity(0.3) : Color.clear, lineWidth: 1)
        )
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Trust Node Row (with hover effects)

struct TrustNodeRow: View {
    let node: TrustNode
    let accentColor: Color
    var onTap: (() -> Void)? = nil
    var onVerify: (() -> Void)? = nil
    var onCopyKey: (() -> Void)? = nil

    @State private var isHovered = false
    @State private var showCopied = false

    private var displayName: String {
        if node.displayMode == .peacetime {
            return node.publicName
        } else {
            return node.alias ?? "Anonymous"
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            // Icon
            Image(systemName: nodeTypeIcon(node.type))
                .font(.system(size: 20))
                .foregroundColor(accentColor)
                .frame(width: 40, height: 40)
                .background(
                    Circle()
                        .fill(accentColor.opacity(isHovered ? 0.25 : 0.15))
                )

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(displayName)
                    .font(.system(size: 14, weight: .medium))

                HStack(spacing: 8) {
                    // Type badge
                    Text(node.type.rawValue.capitalized)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(accentColor)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(accentColor.opacity(0.1))
                        .clipShape(Capsule())

                    if let location = node.location, node.displayMode == .peacetime {
                        HStack(spacing: 4) {
                            Image(systemName: "location")
                                .font(.system(size: 9))
                            Text(location)
                                .font(.system(size: 11))
                        }
                        .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            // Hover actions
            if isHovered {
                HStack(spacing: 4) {
                    TrustActionButton(icon: "checkmark.shield", help: "Verify", color: .green) {
                        onVerify?()
                    }
                    TrustActionButton(icon: showCopied ? "checkmark" : "doc.on.doc", help: "Copy Key", color: showCopied ? .green : .blue, isSuccess: showCopied) {
                        onCopyKey?()
                        withAnimation { showCopied = true }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            withAnimation { showCopied = false }
                        }
                    }
                    TrustActionButton(icon: "hand.thumbsup", help: "Vouch", color: .purple) {
                        onTap?()
                    }
                }
                .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }

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
                .fill(isHovered ? accentColor.opacity(0.08) : Color.gray.opacity(0.06))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(isHovered ? accentColor.opacity(0.3) : accentColor.opacity(0.15), lineWidth: 1)
        )
        .contentShape(Rectangle())
        .onTapGesture {
            onTap?()
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
        .contextMenu {
            Button {
                onVerify?()
            } label: {
                Label("Verify Safety Number", systemImage: "checkmark.shield")
            }

            Button {
                onTap?()
            } label: {
                Label("Vouch for Node", systemImage: "hand.thumbsup")
            }

            Divider()

            Button {
                onCopyKey?()
            } label: {
                Label("Copy Public Key", systemImage: "doc.on.doc")
            }
        }
    }

    private func nodeTypeIcon(_ type: NodeType) -> String {
        switch type {
        case .individual: return "person"
        case .church: return "building.columns"
        case .mission: return "globe"
        case .family: return "person.3"
        case .organization: return "building.2"
        }
    }
}

// MARK: - Trust Action Button

private struct TrustActionButton: View {
    let icon: String
    let help: String
    let color: Color
    var isSuccess: Bool = false
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundColor(isSuccess ? .green : (isHovered ? color : .secondary))
                .frame(width: 26, height: 26)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isSuccess ? Color.green.opacity(0.1) : (isHovered ? color.opacity(0.15) : Color.gray.opacity(0.08)))
                )
        }
        .buttonStyle(.plain)
        .help(help)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Form Field Helper

struct FormField<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                Text(title)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.secondary)
            }
            content()
        }
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    TrustWorkspace()
}
#endif
