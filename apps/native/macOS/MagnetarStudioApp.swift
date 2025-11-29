//
//  MagnetarStudioApp.swift
//  MagnetarStudio (macOS)
//
//  Main app entry point for macOS 26.
//

import SwiftUI
import SwiftData
import AppKit
import UniformTypeIdentifiers

// MARK: - Import shared modules
// All shared code is in the Shared/ folder

@main
struct MagnetarStudioApp: App {
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()
    @StateObject private var databaseStore = DatabaseStore.shared
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var commandPaletteManager = CommandPaletteManager()

    var body: some Scene {
        // Main window
        WindowGroup {
            ContentView()
                .frame(minWidth: 1300, minHeight: 750)
                .onAppear {
                    // Set window size constraints
                    if let window = NSApplication.shared.windows.first {
                        window.setContentSize(NSSize(width: 1400, height: 850))
                        window.minSize = NSSize(width: 1300, height: 750)
                        window.isMovableByWindowBackground = true
                    }
                }
                .sheet(isPresented: $commandPaletteManager.isPresented) {
                    CommandPaletteView(
                        manager: commandPaletteManager,
                        navigationStore: navigationStore,
                        chatStore: chatStore,
                        databaseStore: databaseStore
                    )
                }
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 1400, height: 850)
        .environment(navigationStore)
        .environment(chatStore)
        .environmentObject(databaseStore)
        .environment(commandPaletteManager)
        .commands {
            MagnetarCommands(
                navigationStore: navigationStore,
                chatStore: chatStore,
                databaseStore: databaseStore,
                commandPaletteManager: commandPaletteManager
            )
        }

        // Settings window
        Settings {
            SettingsView()
        }
    }
}

// MARK: - App Delegate for URL Handling

class AppDelegate: NSObject, NSApplicationDelegate {
    @AppStorage("showMenuBar") private var showMenuBar: Bool = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initialize menu bar if enabled
        if showMenuBar {
            MenuBarManager.shared.show()
        }

        // Initialize orchestrators (Phase 4)
        Task {
            await OrchestratorInitializer.initialize()
        }

        // Auto-start Ollama if enabled in settings
        Task {
            await autoStartOllama()
        }
    }

    @MainActor
    private func autoStartOllama() async {
        let settings = SettingsStore.shared.appSettings

        guard settings.ollamaAutoStart else {
            print("Ollama auto-start disabled in settings")
            return
        }

        let ollamaService = OllamaService.shared
        let isRunning = await ollamaService.checkStatus()

        if !isRunning {
            do {
                print("Starting Ollama server (auto-start enabled)...")
                try await ollamaService.start()
                print("✓ Ollama server started successfully")
            } catch {
                print("Failed to auto-start Ollama: \(error)")
            }
        } else {
            print("Ollama server already running")
        }
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            handleURL(url)
        }
    }

    private func handleURL(_ url: URL) {
        guard url.scheme == "magnetarstudio" else { return }

        // Handle auth callback
        if url.host == "auth", url.path == "/callback" {
            Task { @MainActor in
                await CloudAuthManager.shared.handleAuthCallback(url: url)
            }
        }
    }
}

// MARK: - Menu Commands

struct MagnetarCommands: Commands {
    let navigationStore: NavigationStore
    let chatStore: ChatStore
    let databaseStore: DatabaseStore
    let commandPaletteManager: CommandPaletteManager

    private let docsURL = URL(string: "https://docs.magnetar.studio")
    private let issuesURL = URL(string: "https://github.com/MagnetarStudio/MagnetarStudio/issues")

    var body: some Commands {
        // File menu
        CommandGroup(after: .newItem) {
            Button("New Chat Session") {
                Task { await createNewChatSession() }
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("New Query Tab") {
                Task { await createNewQueryTab() }
            }
            .keyboardShortcut("t", modifiers: .command)

            Divider()

            Button("Upload File...") {
                handleFileUpload()
            }
            .keyboardShortcut("o", modifiers: .command)
        }

        // Edit menu (keep defaults)

        // View menu
        CommandMenu("View") {
            Button("Team Workspace") {
                navigationStore.navigate(to: .team)
            }
            .keyboardShortcut("1", modifiers: .command)

            Button("Chat Workspace") {
                navigationStore.navigate(to: .chat)
            }
            .keyboardShortcut("2", modifiers: .command)

            Button("Database Workspace") {
                navigationStore.navigate(to: .database)
            }
            .keyboardShortcut("3", modifiers: .command)

            Button("Kanban Workspace") {
                navigationStore.navigate(to: .kanban)
            }
            .keyboardShortcut("4", modifiers: .command)

            Button("MagnetarHub") {
                navigationStore.navigate(to: .magnetarHub)
            }
            .keyboardShortcut("5", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                navigationStore.toggleSidebar()
            }
            .keyboardShortcut("s", modifiers: [.command, .control])
        }

        // Tools menu
        CommandMenu("Tools") {
            Button("Agent Orchestrator") {
                openAgentOrchestrator()
            }
            .keyboardShortcut("k", modifiers: [.command, .shift])

            Button("Workflow Designer") {
                openWorkflowDesigner()
            }

            Divider()

            Button("Command Palette...") {
                toggleCommandPalette()
            }
            .keyboardShortcut("k", modifiers: .command)
        }

        // Help menu
        CommandGroup(replacing: .help) {
            Button("MagnetarStudio Documentation") {
                openExternal(docsURL)
            }

            Button("Report an Issue") {
                openExternal(issuesURL)
            }

            Divider()

            Button("About MagnetarStudio") {
                NSApp.orderFrontStandardAboutPanel(nil)
            }
        }
    }

    // MARK: - Helpers

    @MainActor
    private func createNewChatSession() async {
        await chatStore.createSession(title: "New Chat", model: chatStore.selectedModel.isEmpty ? "mistral" : chatStore.selectedModel)
        navigationStore.navigate(to: .chat)
    }

    @MainActor
    private func createNewQueryTab() async {
        if databaseStore.sessionId == nil {
            await databaseStore.createSession()
        }
        databaseStore.loadEditorText("", contentType: .sql)
        navigationStore.navigate(to: .database)
    }

    private func handleFileUpload() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType.commaSeparatedText,
            UTType(filenameExtension: "xls"),
            UTType(filenameExtension: "xlsx"),
            UTType.json
        ].compactMap { $0 }
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        if panel.runModal() == .OK, let url = panel.url {
            Task { await uploadSelectedFile(url: url) }
        }
    }

    @MainActor
    private func uploadSelectedFile(url: URL) async {
        if databaseStore.sessionId == nil {
            await databaseStore.createSession()
        }
        await databaseStore.uploadFile(url: url)
        navigationStore.navigate(to: .database)
    }

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }

    // MARK: - Tool Menu Commands

    private func openAgentOrchestrator() {
        navigationStore.navigate(to: .magnetarHub)
    }

    private func openWorkflowDesigner() {
        navigationStore.navigate(to: .kanban)
    }

    private func toggleCommandPalette() {
        commandPaletteManager.toggle()
    }
}

// MARK: - Command Palette

@Observable
final class CommandPaletteManager {
    var isPresented: Bool = false

    func toggle() {
        isPresented.toggle()
    }

    func present() {
        isPresented = true
    }

    func dismiss() {
        isPresented = false
    }
}

struct CommandPaletteView: View {
    let manager: CommandPaletteManager
    let navigationStore: NavigationStore
    let chatStore: ChatStore
    let databaseStore: DatabaseStore

    @State private var searchText: String = ""
    @State private var selectedIndex: Int = 0
    @FocusState private var isSearchFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Search field
            HStack(spacing: 12) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)

                TextField("Type a command...", text: $searchText)
                    .textFieldStyle(.plain)
                    .focused($isSearchFocused)
                    .font(.system(size: 16))
                    .onSubmit {
                        executeSelectedCommand()
                    }

                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(16)
            .background(Color(nsColor: .controlBackgroundColor))

            Divider()

            // Commands list
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(Array(filteredCommands.enumerated()), id: \.element.id) { index, command in
                        CommandRow(
                            command: command,
                            isSelected: index == selectedIndex
                        )
                        .contentShape(Rectangle())
                        .onTapGesture {
                            selectedIndex = index
                            executeCommand(command)
                        }
                    }
                }
            }
            .frame(maxHeight: 400)
        }
        .frame(width: 600)
        .background(Color(nsColor: .windowBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.3), radius: 20, x: 0, y: 10)
        .onAppear {
            isSearchFocused = true
        }
        .onKeyPress(.escape) {
            manager.dismiss()
            return .handled
        }
        .onKeyPress(.downArrow) {
            if selectedIndex < filteredCommands.count - 1 {
                selectedIndex += 1
            }
            return .handled
        }
        .onKeyPress(.upArrow) {
            if selectedIndex > 0 {
                selectedIndex -= 1
            }
            return .handled
        }
        .onKeyPress(.return) {
            executeSelectedCommand()
            return .handled
        }
    }

    // MARK: - Commands

    private var allCommands: [PaletteCommand] {
        [
            // Navigation
            PaletteCommand(
                id: "nav-team",
                title: "Go to Team Workspace",
                subtitle: "Team collaboration and vault",
                icon: "person.2",
                category: .navigation,
                keywords: ["team", "vault", "members"],
                action: { navigationStore.navigate(to: .team) }
            ),
            PaletteCommand(
                id: "nav-chat",
                title: "Go to Chat Workspace",
                subtitle: "AI conversations",
                icon: "message",
                category: .navigation,
                keywords: ["chat", "conversation", "ai"],
                action: { navigationStore.navigate(to: .chat) }
            ),
            PaletteCommand(
                id: "nav-database",
                title: "Go to Database Workspace",
                subtitle: "Query and analyze data",
                icon: "cylinder",
                category: .navigation,
                keywords: ["database", "query", "sql", "data"],
                action: { navigationStore.navigate(to: .database) }
            ),
            PaletteCommand(
                id: "nav-kanban",
                title: "Go to Kanban Workspace",
                subtitle: "Project management",
                icon: "square.grid.2x2",
                category: .navigation,
                keywords: ["kanban", "tasks", "project"],
                action: { navigationStore.navigate(to: .kanban) }
            ),
            PaletteCommand(
                id: "nav-hub",
                title: "Go to MagnetarHub",
                subtitle: "Cloud models and agents",
                icon: "cloud",
                category: .navigation,
                keywords: ["hub", "cloud", "models", "agents", "orchestrator"],
                action: { navigationStore.navigate(to: .magnetarHub) }
            ),

            // Actions
            PaletteCommand(
                id: "new-chat",
                title: "New Chat Session",
                subtitle: "Start a new AI conversation",
                icon: "plus.message",
                category: .action,
                keywords: ["new", "chat", "create"],
                action: {
                    Task {
                        await chatStore.createSession(
                            title: "New Chat",
                            model: chatStore.selectedModel.isEmpty ? "mistral" : chatStore.selectedModel
                        )
                        navigationStore.navigate(to: .chat)
                    }
                }
            ),
            PaletteCommand(
                id: "new-query",
                title: "New Query Tab",
                subtitle: "Create a new database query",
                icon: "doc.text",
                category: .action,
                keywords: ["new", "query", "sql", "database"],
                action: {
                    Task {
                        if databaseStore.sessionId == nil {
                            await databaseStore.createSession()
                        }
                        databaseStore.loadEditorText("", contentType: .sql)
                        navigationStore.navigate(to: .database)
                    }
                }
            ),

            // Tools
            PaletteCommand(
                id: "agent-orchestrator",
                title: "Agent Orchestrator",
                subtitle: "Manage AI agents",
                icon: "brain",
                category: .tools,
                keywords: ["agent", "orchestrator", "ai"],
                action: { navigationStore.navigate(to: .magnetarHub) }
            ),
            PaletteCommand(
                id: "workflow-designer",
                title: "Workflow Designer",
                subtitle: "Design and manage workflows",
                icon: "flowchart",
                category: .tools,
                keywords: ["workflow", "designer", "automation"],
                action: { navigationStore.navigate(to: .kanban) }
            ),

            // Settings
            PaletteCommand(
                id: "settings",
                title: "Open Settings",
                subtitle: "Configure MagnetarStudio",
                icon: "gear",
                category: .settings,
                keywords: ["settings", "preferences", "config"],
                action: {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                }
            ),

            // View
            PaletteCommand(
                id: "toggle-sidebar",
                title: "Toggle Sidebar",
                subtitle: "Show or hide the sidebar",
                icon: "sidebar.left",
                category: .view,
                keywords: ["sidebar", "toggle", "hide", "show"],
                action: { navigationStore.toggleSidebar() }
            ),
        ]
    }

    private var filteredCommands: [PaletteCommand] {
        if searchText.isEmpty {
            return allCommands
        }

        let query = searchText.lowercased()
        return allCommands.filter { command in
            command.title.lowercased().contains(query) ||
            command.subtitle.lowercased().contains(query) ||
            command.keywords.contains(where: { $0.contains(query) })
        }
    }

    // MARK: - Actions

    private func executeSelectedCommand() {
        guard selectedIndex < filteredCommands.count else { return }
        executeCommand(filteredCommands[selectedIndex])
    }

    private func executeCommand(_ command: PaletteCommand) {
        manager.dismiss()
        command.action()
    }
}

// MARK: - Command Row

struct CommandRow: View {
    let command: PaletteCommand
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: command.icon)
                .font(.system(size: 18))
                .foregroundStyle(isSelected ? .white : .primary)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 2) {
                Text(command.title)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(isSelected ? .white : .primary)

                Text(command.subtitle)
                    .font(.system(size: 12))
                    .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)
            }

            Spacer()

            Text(command.category.displayName)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 3)
                .background(
                    Capsule()
                        .fill(isSelected ? Color.white.opacity(0.2) : Color.secondary.opacity(0.1))
                )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(isSelected ? Color.accentColor : Color.clear)
        .contentShape(Rectangle())
    }
}

// MARK: - Palette Command

struct PaletteCommand: Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let icon: String
    let category: CommandCategory
    let keywords: [String]
    let action: () -> Void

    enum CommandCategory {
        case navigation
        case action
        case tools
        case settings
        case view

        var displayName: String {
            switch self {
            case .navigation: return "Go"
            case .action: return "New"
            case .tools: return "Tools"
            case .settings: return "Settings"
            case .view: return "View"
            }
        }
    }
}
