//
//  SettingsView.swift
//  MedStation
//
//  Settings panel accessible via menu bar.
//

import SwiftUI
import AppKit
import ServiceManagement
import UserNotifications
import Observation

/// Settings tab identifiers — used for programmatic tab selection
enum SettingsTab: String {
    case general, features, api, security, appearance, models
}

struct SettingsView: View {
    // Default from centralized config - user can override in settings
    @AppStorage("apiBaseURL") private var apiBaseURL = APIConfiguration.shared.baseURL
    @AppStorage("defaultModel") private var defaultModel = "mistral"
    @AppStorage("enableBiometrics") private var enableBiometrics = true
    @AppStorage("theme") private var theme = "system"
    @AppStorage("settings.selectedTab") private var selectedTab: String = SettingsTab.general.rawValue

    var body: some View {
        TabView(selection: $selectedTab) {
            GeneralSettingsView()
                .tabItem {
                    Label("General", systemImage: "gear")
                }
                .tag(SettingsTab.general.rawValue)

            FeaturesSettingsView()
                .tabItem {
                    Label("Features", systemImage: "puzzlepiece.extension")
                }
                .tag(SettingsTab.features.rawValue)

            APISettingsView(apiBaseURL: $apiBaseURL, defaultModel: $defaultModel)
                .tabItem {
                    Label("API", systemImage: "network")
                }
                .tag(SettingsTab.api.rawValue)

            SecuritySettingsView(enableBiometrics: $enableBiometrics)
                .tabItem {
                    Label("Security", systemImage: "lock.shield")
                }
                .tag(SettingsTab.security.rawValue)

            AppearanceSettingsView(theme: $theme)
                .tabItem {
                    Label("Appearance", systemImage: "paintbrush")
                }
                .tag(SettingsTab.appearance.rawValue)

            ModelManagementSettingsView()
                .tabItem {
                    Label("Models", systemImage: "cpu")
                }
                .tag(SettingsTab.models.rawValue)
        }
        .frame(minWidth: 600, idealWidth: 600, maxWidth: .infinity,
               minHeight: 500, idealHeight: 500, maxHeight: .infinity)
    }
}


// MARK: - Settings Manager

@MainActor
@Observable
final class SettingsManager {
    static let shared = SettingsManager()

    // MARK: - Launch at Login
    // Note: @AppStorage requires @ObservationIgnored with @Observable
    @ObservationIgnored
    @AppStorage("launchAtLogin") var launchAtLogin: Bool = false {
        didSet {
            if launchAtLogin != oldValue {
                Task {
                    await toggleLaunchAtLogin(enabled: launchAtLogin)
                }
            }
        }
    }
    var launchAtLoginStatus: SimpleStatus = .idle

    // MARK: - Menu Bar
    @ObservationIgnored
    @AppStorage("showMenuBar") var showMenuBar: Bool = false {
        didSet {
            if showMenuBar != oldValue {
                toggleMenuBar(enabled: showMenuBar)
            }
        }
    }
    var menuBarStatus: SimpleStatus = .idle

    // MARK: - Notifications
    @ObservationIgnored
    @AppStorage("notificationsEnabled") var notificationsEnabled: Bool = false {
        didSet {
            if notificationsEnabled != oldValue {
                Task {
                    await toggleNotifications(enabled: notificationsEnabled)
                }
            }
        }
    }
    var notificationsStatus: SimpleStatus = .idle

    private init() {}

    // MARK: - Check Initial States

    func checkInitialStates() async {
        // Check launch at login status
        if #available(macOS 13.0, *) {
            let service = SMAppService.mainApp
            launchAtLogin = (service.status == .enabled)
        }

        // Check notification authorization
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()

        switch settings.authorizationStatus {
        case .authorized:
            notificationsEnabled = true
            notificationsStatus = .idle
        case .denied:
            notificationsEnabled = false
            notificationsStatus = .failure("Notifications denied in System Settings")
        case .notDetermined:
            notificationsStatus = .idle
        default:
            notificationsStatus = .idle
        }
    }

    // MARK: - Launch at Login

    private func toggleLaunchAtLogin(enabled: Bool) async {
        guard #available(macOS 13.0, *) else {
            launchAtLoginStatus = .failure("Requires macOS 13+")
            launchAtLogin = false
            return
        }

        launchAtLoginStatus = .loading

        do {
            let service = SMAppService.mainApp

            if enabled {
                try service.register()
                launchAtLoginStatus = .success("Enabled")
            } else {
                try await service.unregister()
                launchAtLoginStatus = .success("Disabled")
            }

            // Auto-clear success message
            try? await Task.sleep(for: .seconds(2))
            if launchAtLoginStatus.isSuccess {
                launchAtLoginStatus = .idle
            }
        } catch {
            launchAtLoginStatus = .failure(error.localizedDescription)
            launchAtLogin = !enabled // Revert toggle
        }
    }

    // MARK: - Menu Bar

    private func toggleMenuBar(enabled: Bool) {
        menuBarStatus = .loading

        if enabled {
            MenuBarManager.shared.show()
            menuBarStatus = .success("Menu bar icon enabled")
        } else {
            MenuBarManager.shared.hide()
            menuBarStatus = .success("Menu bar icon hidden")
        }

        // Auto-clear success message
        Task {
            try? await Task.sleep(for: .seconds(2))
            if menuBarStatus.isSuccess {
                menuBarStatus = .idle
            }
        }
    }

    // MARK: - Notifications

    private func toggleNotifications(enabled: Bool) async {
        notificationsStatus = .loading

        let center = UNUserNotificationCenter.current()

        if enabled {
            // Request authorization
            do {
                let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])

                if granted {
                    notificationsEnabled = true
                    notificationsStatus = .success("Notifications enabled")
                } else {
                    notificationsEnabled = false
                    notificationsStatus = .failure("Notifications denied")
                }
            } catch {
                notificationsEnabled = false
                notificationsStatus = .failure(error.localizedDescription)
            }
        } else {
            // Cannot programmatically revoke - user must do it in System Settings
            notificationsEnabled = false
            notificationsStatus = .success("Disabled (revoke in System Settings if needed)")
        }

        // Auto-clear success message
        try? await Task.sleep(for: .seconds(3))
        if notificationsStatus.isSuccess {
            notificationsStatus = .idle
        }
    }
}

// MARK: - Menu Bar Manager

final class MenuBarManager {
    static let shared = MenuBarManager()

    private var statusItem: NSStatusItem?

    private init() {}

    func show() {
        guard statusItem == nil else { return }

        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)

        if let button = item.button {
            button.image = NSImage(systemSymbolName: "cube.box.fill", accessibilityDescription: "MedStation")
            button.action = #selector(handleMenuBarClick)
            button.target = self
        }

        // Create menu
        let menu = NSMenu()

        menu.addItem(NSMenuItem(title: "Open MedStation", action: #selector(openMainWindow), keyEquivalent: "o"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(openSettings), keyEquivalent: ","))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))

        item.menu = menu
        statusItem = item
    }

    func hide() {
        guard let item = statusItem else { return }
        NSStatusBar.system.removeStatusItem(item)
        statusItem = nil
    }

    @objc private func handleMenuBarClick() {
        // Menu is shown automatically
    }

    @objc private func openMainWindow() {
        NSApp.activate(ignoringOtherApps: true)
        if let window = NSApp.windows.first {
            window.makeKeyAndOrderFront(nil)
        }
    }

    @objc private func openSettings() {
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
}
