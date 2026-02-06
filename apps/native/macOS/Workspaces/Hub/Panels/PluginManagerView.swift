//
//  PluginManagerView.swift
//  MagnetarStudio (macOS)
//
//  Grid/list of installed plugins with toggle enable/disable,
//  plugin detail view, and install from file.
//

import SwiftUI
import UniformTypeIdentifiers

struct PluginManagerView: View {
    @State private var pluginManager = PluginManager.shared
    @State private var selectedPlugin: InstalledPlugin?
    @State private var searchText = ""
    @State private var showInstallPanel = false
    @State private var installError: String?

    private var filteredPlugins: [InstalledPlugin] {
        if searchText.isEmpty { return pluginManager.plugins }
        return pluginManager.plugins.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            $0.manifest.description.localizedCaseInsensitiveContains(searchText)
        }
    }

    private var builtinPlugins: [InstalledPlugin] {
        filteredPlugins.filter { $0.manifest.id.hasPrefix("com.magnetar.builtin.") }
    }

    private var userPlugins: [InstalledPlugin] {
        filteredPlugins.filter { !$0.manifest.id.hasPrefix("com.magnetar.builtin.") }
    }

    var body: some View {
        VStack(spacing: 0) {
            toolbar
            Divider()

            if pluginManager.isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                HSplitView {
                    pluginList
                        .frame(minWidth: 280, maxWidth: .infinity)

                    if let plugin = selectedPlugin {
                        PluginDetailView(plugin: plugin)
                            .frame(minWidth: 260, idealWidth: 300)
                    }
                }
            }
        }
        .task {
            if pluginManager.isLoading {
                await pluginManager.loadAll()
            }
        }
        .fileImporter(
            isPresented: $showInstallPanel,
            allowedContentTypes: [.folder],
            allowsMultipleSelection: false
        ) { result in
            if case .success(let urls) = result, let url = urls.first {
                Task {
                    do {
                        try await pluginManager.installPlugin(from: url)
                    } catch {
                        installError = error.localizedDescription
                    }
                }
            }
        }
        .alert("Plugin Install Failed", isPresented: Binding(
            get: { installError != nil },
            set: { if !$0 { installError = nil } }
        )) {
            Button("OK") { installError = nil }
        } message: {
            Text(installError ?? "")
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 10) {
            Image(systemName: "puzzlepiece.extension")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)

            Text("Plugins")
                .font(.system(size: 14, weight: .semibold))

            Text("(\(pluginManager.activePlugins.count) active)")
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)

            Spacer()

            // Search
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                TextField("Search...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .frame(width: 120)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.gray.opacity(0.1))
            )

            Button {
                showInstallPanel = true
            } label: {
                Image(systemName: "plus")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .help("Install Plugin")
        }
        .padding(.horizontal, 16)
        .frame(height: HubLayout.headerHeight)
    }

    // MARK: - Plugin List

    private var pluginList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                // Built-in section
                if !builtinPlugins.isEmpty {
                    sectionHeader("Built-in", count: builtinPlugins.count)
                    ForEach(builtinPlugins) { plugin in
                        pluginRow(plugin)
                    }
                }

                // User plugins section
                if !userPlugins.isEmpty {
                    sectionHeader("Installed", count: userPlugins.count)
                    ForEach(userPlugins) { plugin in
                        pluginRow(plugin)
                    }
                }

                // Empty state for user plugins
                if userPlugins.isEmpty && searchText.isEmpty {
                    VStack(spacing: 8) {
                        Text("No user plugins installed")
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                        Text("Drop a plugin bundle here or click + to install")
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 20)
                }
            }
            .padding(16)
        }
    }

    private func sectionHeader(_ title: String, count: Int) -> some View {
        HStack {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)
            Text("(\(count))")
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
            Spacer()
        }
    }

    private func pluginRow(_ plugin: InstalledPlugin) -> some View {
        let isSelected = selectedPlugin?.id == plugin.id
        return Button {
            selectedPlugin = plugin
        } label: {
            HStack(spacing: 12) {
                // Icon
                Image(systemName: plugin.icon)
                    .font(.system(size: 18))
                    .foregroundStyle(plugin.isActive ? Color.accentColor : Color.secondary)
                    .frame(width: 28, height: 28)

                // Info
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(plugin.name)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(.primary)
                        Text("v\(plugin.version)")
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }

                    Text(plugin.manifest.description)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)

                    // Capabilities
                    HStack(spacing: 4) {
                        ForEach(plugin.manifest.capabilities) { cap in
                            Text(cap.displayName)
                                .font(.system(size: 9, weight: .medium))
                                .foregroundStyle(.secondary)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(
                                    RoundedRectangle(cornerRadius: 3)
                                        .fill(Color.gray.opacity(0.1))
                                )
                        }
                    }
                }

                Spacer()

                // Status indicator
                if case .errored = plugin.state {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 12))
                        .foregroundStyle(.orange)
                }

                // Toggle (not for built-ins)
                if !plugin.manifest.id.hasPrefix("com.magnetar.builtin.") {
                    Toggle("", isOn: Binding(
                        get: { plugin.isActive },
                        set: { _ in pluginManager.togglePlugin(plugin.id) }
                    ))
                    .labelsHidden()
                    .toggleStyle(.switch)
                    .controlSize(.small)
                } else {
                    Text("Built-in")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(10)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.08) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.accentColor.opacity(0.3) : Color.clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Plugin Detail View

struct PluginDetailView: View {
    let plugin: InstalledPlugin
    @State private var showSettings = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Header
                VStack(alignment: .leading, spacing: 8) {
                    Image(systemName: plugin.icon)
                        .font(.system(size: 28))
                        .foregroundStyle(Color.accentColor)

                    Text(plugin.name)
                        .font(.system(size: 16, weight: .semibold))

                    Text(plugin.manifest.description)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }

                Divider()

                // Info grid
                infoRow("Version", value: plugin.version)
                infoRow("Author", value: plugin.manifest.author)
                infoRow("Status", value: plugin.state.displayName)

                if let loadedAt = plugin.state.loadedAt {
                    infoRow("Loaded", value: loadedAt.formatted(.dateTime.hour().minute()))
                }

                if let error = plugin.state.errorMessage {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Error")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(.red)
                        Text(error)
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                }

                Divider()

                // Capabilities
                Text("CAPABILITIES")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(.secondary)

                ForEach(plugin.manifest.capabilities) { cap in
                    HStack(spacing: 8) {
                        Image(systemName: cap.icon)
                            .font(.system(size: 12))
                            .foregroundStyle(Color.accentColor)
                            .frame(width: 16)
                        Text(cap.displayName)
                            .font(.system(size: 12))
                    }
                }

                Divider()

                // Permissions
                Text("PERMISSIONS")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(.secondary)

                permissionRow("Network", allowed: plugin.manifest.permissions.network, icon: "network")
                permissionRow("File Read", allowed: plugin.manifest.permissions.fileRead, icon: "doc")
                permissionRow("File Write", allowed: plugin.manifest.permissions.fileWrite, icon: "doc.badge.plus")
                permissionRow("Clipboard", allowed: plugin.manifest.permissions.clipboard, icon: "doc.on.clipboard")

                // Settings button
                if !plugin.manifest.settings.isEmpty {
                    Divider()
                    Button("Plugin Settings...") {
                        showSettings = true
                    }
                    .controlSize(.small)
                }
            }
            .padding(16)
        }
        .sheet(isPresented: $showSettings) {
            PluginSettingsView(plugin: plugin)
        }
    }

    private func infoRow(_ label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .frame(width: 60, alignment: .leading)
            Text(value)
                .font(.system(size: 11, weight: .medium))
        }
    }

    private func permissionRow(_ label: String, allowed: Bool, icon: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(allowed ? .green : .secondary)
                .frame(width: 16)
            Text(label)
                .font(.system(size: 11))
            Spacer()
            Image(systemName: allowed ? "checkmark.circle.fill" : "minus.circle")
                .font(.system(size: 11))
                .foregroundStyle(allowed ? .green : .secondary)
        }
    }
}
