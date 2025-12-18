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

// MARK: - Register Node Modal

struct RegisterNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let onRegister: (TrustNode) -> Void

    @State private var publicName: String = ""
    @State private var alias: String = ""
    @State private var nodeType: NodeType = .individual
    @State private var bio: String = ""
    @State private var location: String = ""
    @State private var displayMode: DisplayMode = .peacetime
    @State private var generatedPublicKey: String = ""

    @State private var isRegistering: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Register Trust Node")
                        .font(.system(size: 20, weight: .bold))
                    Text("Join the MagnetarTrust network")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(24)

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Public Name
                    FormField(title: "Public Name *", icon: "person") {
                        TextField("Your name or church name", text: $publicName)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Node Type
                    FormField(title: "Type *", icon: "building.columns") {
                        Picker("", selection: $nodeType) {
                            ForEach([NodeType.individual, .church, .mission, .family, .organization], id: \.self) { type in
                                Text(type.rawValue.capitalized).tag(type)
                            }
                        }
                        .pickerStyle(.segmented)
                    }

                    // Alias (Underground mode)
                    FormField(title: "Alias (Underground Mode)", icon: "theatermasks") {
                        TextField("Pseudonym or code name", text: $alias)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Display Mode
                    FormField(title: "Display Mode *", icon: "eye") {
                        Picker("", selection: $displayMode) {
                            Text("Peacetime").tag(DisplayMode.peacetime)
                            Text("Underground").tag(DisplayMode.underground)
                        }
                        .pickerStyle(.segmented)
                    }

                    // Bio
                    FormField(title: "Bio", icon: "doc.text") {
                        TextEditor(text: $bio)
                            .frame(height: 80)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
                    }

                    // Location
                    FormField(title: "Location", icon: "location") {
                        TextField("City, Country", text: $location)
                            .textFieldStyle(.roundedBorder)
                    }

                    // Public Key (Generated)
                    FormField(title: "Public Key", icon: "key") {
                        HStack {
                            Text(generatedPublicKey.isEmpty ? "Will be generated on save" : generatedPublicKey)
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                            Spacer()
                            if !generatedPublicKey.isEmpty {
                                Button {
                                    generateKeys()
                                } label: {
                                    Image(systemName: "arrow.clockwise")
                                }
                                .buttonStyle(.plain)
                                .help("Regenerate keys")
                            }
                        }
                        .padding(8)
                        .background(Color.gray.opacity(0.05))
                        .cornerRadius(6)
                    }

                    if let error = errorMessage {
                        Text(error)
                            .font(.system(size: 13))
                            .foregroundColor(.red)
                            .padding(12)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.red.opacity(0.1))
                            )
                    }
                }
                .padding(24)
            }

            Divider()

            // Footer
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)

                Spacer()

                Button {
                    Task {
                        await registerNode()
                    }
                } label: {
                    if isRegistering {
                        ProgressView()
                            .scaleEffect(0.8)
                            .frame(width: 100)
                    } else {
                        Text("Register")
                            .frame(width: 100)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isRegistering || publicName.isEmpty)
            }
            .padding(24)
        }
        .frame(width: 600, height: 700)
        .onAppear {
            generateKeys()
        }
    }

    private func generateKeys() {
        // Simple key generation (UUID-based for MVP)
        // TODO: Use proper cryptographic key generation (Ed25519, etc.)
        generatedPublicKey = "node_\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(32))"
    }

    private func registerNode() async {
        isRegistering = true
        errorMessage = nil
        defer { isRegistering = false }

        do {
            let request = RegisterNodeRequest(
                publicKey: generatedPublicKey,
                publicName: publicName,
                type: nodeType,
                alias: alias.isEmpty ? nil : alias,
                bio: bio.isEmpty ? nil : bio,
                location: location.isEmpty ? nil : location,
                displayMode: displayMode
            )

            let node = try await TrustService.shared.registerNode(request)
            print("✅ Node registered: \(node.id)")
            onRegister(node)
            dismiss()
        } catch {
            errorMessage = "Failed to register: \(error.localizedDescription)"
            print("❌ Registration failed: \(error)")
        }
    }
}

// MARK: - Vouch Modal

struct VouchNodeModal: View {
    @Environment(\.dismiss) private var dismiss
    let node: TrustNode
    let onVouched: () -> Void

    @State private var trustLevel: TrustLevel = .vouched
    @State private var note: String = ""
    @State private var isVouching: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Vouch for \(node.publicName)")
                        .font(.system(size: 20, weight: .bold))
                    Text("Create a trust relationship")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(24)

            Divider()

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Node info
                    HStack(spacing: 12) {
                        Image(systemName: nodeTypeIcon(node.type))
                            .font(.system(size: 24))
                            .foregroundColor(.magnetarPrimary)
                            .frame(width: 48, height: 48)
                            .background(
                                Circle()
                                    .fill(Color.magnetarPrimary.opacity(0.15))
                            )

                        VStack(alignment: .leading, spacing: 4) {
                            Text(node.publicName)
                                .font(.system(size: 16, weight: .medium))
                            Text(node.type.rawValue.capitalized)
                                .font(.system(size: 13))
                                .foregroundColor(.secondary)
                            if let location = node.location {
                                Text(location)
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    .padding(16)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.gray.opacity(0.05))
                    )

                    // Trust Level
                    FormField(title: "Trust Level *", icon: "hand.thumbsup") {
                        VStack(spacing: 12) {
                            trustLevelOption(
                                level: .direct,
                                title: "Direct Trust",
                                description: "I know this person/organization personally",
                                color: .green
                            )
                            trustLevelOption(
                                level: .vouched,
                                title: "Vouched",
                                description: "I vouch for this node based on recommendation",
                                color: .blue
                            )
                        }
                    }

                    // Note
                    FormField(title: "Note (Optional)", icon: "note.text") {
                        TextEditor(text: $note)
                            .frame(height: 100)
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )
                    }

                    if let error = errorMessage {
                        Text(error)
                            .font(.system(size: 13))
                            .foregroundColor(.red)
                            .padding(12)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.red.opacity(0.1))
                            )
                    }
                }
                .padding(24)
            }

            Divider()

            // Footer
            HStack {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)

                Spacer()

                Button {
                    Task {
                        await vouchForNode()
                    }
                } label: {
                    if isVouching {
                        ProgressView()
                            .scaleEffect(0.8)
                            .frame(width: 100)
                    } else {
                        Text("Vouch")
                            .frame(width: 100)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isVouching)
            }
            .padding(24)
        }
        .frame(width: 500, height: 550)
    }

    private func trustLevelOption(level: TrustLevel, title: String, description: String, color: Color) -> some View {
        Button {
            trustLevel = level
        } label: {
            HStack(spacing: 12) {
                Image(systemName: trustLevel == level ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 20))
                    .foregroundColor(trustLevel == level ? color : .secondary)

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.primary)
                    Text(description)
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(trustLevel == level ? color : Color.gray.opacity(0.3), lineWidth: trustLevel == level ? 2 : 1)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(trustLevel == level ? color.opacity(0.05) : Color.clear)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    private func vouchForNode() async {
        isVouching = true
        errorMessage = nil
        defer { isVouching = false }

        do {
            let request = VouchRequest(
                targetNodeId: node.id,
                level: trustLevel,
                note: note.isEmpty ? nil : note
            )

            let relationship = try await TrustService.shared.vouchForNode(request)
            print("✅ Vouched for \(node.publicName): \(relationship.id)")
            onVouched()
            dismiss()
        } catch {
            errorMessage = "Failed to vouch: \(error.localizedDescription)"
            print("❌ Vouching failed: \(error)")
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
