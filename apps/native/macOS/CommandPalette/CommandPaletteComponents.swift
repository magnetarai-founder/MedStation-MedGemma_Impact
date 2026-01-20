//
//  CommandPaletteComponents.swift
//  MagnetarStudio (macOS)
//
//  Command palette UI components - Extracted from MagnetarStudioApp.swift (Phase 6.15)
//  Provides command palette manager, view, and command models
//

import SwiftUI

// MARK: - Command Palette Manager

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

// MARK: - Command Palette View

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

            // Commands list with section headers
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(groupedCommands, id: \.category) { group in
                            // Section header
                            CommandSectionHeader(title: group.category.displayName)

                            // Commands in section
                            ForEach(group.commands) { command in
                                let index = flatIndex(for: command)
                                CommandRow(
                                    command: command,
                                    isSelected: index == selectedIndex
                                )
                                .id(command.id)
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    selectedIndex = index
                                    executeCommand(command)
                                }
                            }
                        }
                    }
                }
                .frame(maxHeight: 400)
                .onChange(of: selectedIndex) { _, newIndex in
                    if let command = filteredCommands[safe: newIndex] {
                        withAnimation(.easeInOut(duration: 0.15)) {
                            proxy.scrollTo(command.id, anchor: .center)
                        }
                    }
                }
            }
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
        var commands: [PaletteCommand] = []

        // Recent chats (dynamic)
        commands.append(contentsOf: recentChatCommands)

        // Actions - Create new things
        commands.append(contentsOf: [
            PaletteCommand(
                id: "new-note",
                title: "New Note",
                subtitle: "Create a standalone note",
                icon: "doc.badge.plus",
                category: .action,
                keywords: ["new", "note", "create", "document"],
                shortcut: "⇧⌘N",
                action: { WindowOpener.shared.openNewNote() }
            ),
            PaletteCommand(
                id: "new-chat-window",
                title: "New Chat Window",
                subtitle: "Open chat in separate window",
                icon: "message.badge.plus",
                category: .action,
                keywords: ["new", "chat", "window", "create"],
                shortcut: "⇧⌘C",
                action: { WindowOpener.shared.openNewChat() }
            ),
            PaletteCommand(
                id: "new-chat",
                title: "New Chat Session",
                subtitle: "Start a new AI conversation",
                icon: "plus.message",
                category: .action,
                keywords: ["new", "chat", "create", "session"],
                shortcut: "⌘N",
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
                shortcut: "⌘T",
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
        ])

        // Navigation - Switch workspaces in main window
        commands.append(contentsOf: [
            PaletteCommand(
                id: "nav-team",
                title: "Go to Team Workspace",
                subtitle: "Team collaboration and vault",
                icon: "person.2",
                category: .navigation,
                keywords: ["team", "vault", "members", "files"],
                shortcut: "⌘1",
                action: { navigationStore.navigate(to: .team) }
            ),
            PaletteCommand(
                id: "nav-chat",
                title: "Go to Chat Workspace",
                subtitle: "AI conversations",
                icon: "message",
                category: .navigation,
                keywords: ["chat", "conversation", "ai"],
                shortcut: "⌘2",
                action: { navigationStore.navigate(to: .chat) }
            ),
            PaletteCommand(
                id: "nav-code",
                title: "Go to Code Workspace",
                subtitle: "Code editing and generation",
                icon: "chevron.left.forwardslash.chevron.right",
                category: .navigation,
                keywords: ["code", "editor", "programming"],
                shortcut: "⌘3",
                action: { navigationStore.navigate(to: .code) }
            ),
            PaletteCommand(
                id: "nav-database",
                title: "Go to Database Workspace",
                subtitle: "Query and analyze data",
                icon: "cylinder",
                category: .navigation,
                keywords: ["database", "query", "sql", "data"],
                shortcut: "⌘4",
                action: { navigationStore.navigate(to: .database) }
            ),
            PaletteCommand(
                id: "nav-kanban",
                title: "Go to Kanban Workspace",
                subtitle: "Project management",
                icon: "square.grid.2x2",
                category: .navigation,
                keywords: ["kanban", "tasks", "project", "board"],
                shortcut: "⌘5",
                action: { navigationStore.navigate(to: .kanban) }
            ),
            PaletteCommand(
                id: "nav-insights",
                title: "Go to Insights Workspace",
                subtitle: "Analytics and reports",
                icon: "chart.xyaxis.line",
                category: .navigation,
                keywords: ["insights", "analytics", "reports", "charts"],
                shortcut: "⌘6",
                action: { navigationStore.navigate(to: .insights) }
            ),
            PaletteCommand(
                id: "nav-trust",
                title: "Go to Trust Network",
                subtitle: "P2P connections and identity",
                icon: "shield.checkered",
                category: .navigation,
                keywords: ["trust", "network", "p2p", "identity", "security"],
                shortcut: "⌘7",
                action: { navigationStore.navigate(to: .trust) }
            ),
            PaletteCommand(
                id: "nav-hub",
                title: "Go to MagnetarHub",
                subtitle: "Cloud models and agents",
                icon: "cloud",
                category: .navigation,
                keywords: ["hub", "cloud", "models", "agents", "orchestrator"],
                shortcut: "⌘8",
                action: { navigationStore.navigate(to: .magnetarHub) }
            ),
        ])

        // Window - Open in separate windows
        commands.append(contentsOf: [
            PaletteCommand(
                id: "window-code",
                title: "Open Code Window",
                subtitle: "Code workspace in new window",
                icon: "uiwindow.split.2x1",
                category: .window,
                keywords: ["window", "code", "detach"],
                shortcut: "⌥⌘C",
                action: { WindowOpener.shared.openCodeWorkspace() }
            ),
            PaletteCommand(
                id: "window-database",
                title: "Open Database Window",
                subtitle: "Database workspace in new window",
                icon: "uiwindow.split.2x1",
                category: .window,
                keywords: ["window", "database", "detach"],
                shortcut: "⇧⌘D",
                action: { WindowOpener.shared.openDatabaseWorkspace() }
            ),
            PaletteCommand(
                id: "window-kanban",
                title: "Open Kanban Window",
                subtitle: "Kanban workspace in new window",
                icon: "uiwindow.split.2x1",
                category: .window,
                keywords: ["window", "kanban", "detach"],
                shortcut: "⇧⌘K",
                action: { WindowOpener.shared.openKanbanWorkspace() }
            ),
            PaletteCommand(
                id: "window-insights",
                title: "Open Insights Window",
                subtitle: "Insights workspace in new window",
                icon: "uiwindow.split.2x1",
                category: .window,
                keywords: ["window", "insights", "detach"],
                shortcut: "⇧⌘I",
                action: { WindowOpener.shared.openInsightsWorkspace() }
            ),
            PaletteCommand(
                id: "model-manager",
                title: "Model Manager",
                subtitle: "Manage local AI models",
                icon: "cpu",
                category: .window,
                keywords: ["model", "manager", "ollama", "ai"],
                shortcut: "⌘M",
                action: { WindowOpener.shared.openModelManager() }
            ),
        ])

        // Tools
        commands.append(contentsOf: [
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
        ])

        // View
        commands.append(contentsOf: [
            PaletteCommand(
                id: "toggle-sidebar",
                title: "Toggle Sidebar",
                subtitle: "Show or hide the sidebar",
                icon: "sidebar.left",
                category: .view,
                keywords: ["sidebar", "toggle", "hide", "show"],
                shortcut: "⌃⌘S",
                action: { navigationStore.toggleSidebar() }
            ),
        ])

        // Settings
        commands.append(contentsOf: [
            PaletteCommand(
                id: "settings",
                title: "Open Settings",
                subtitle: "Configure MagnetarStudio",
                icon: "gear",
                category: .settings,
                keywords: ["settings", "preferences", "config"],
                shortcut: "⌘,",
                action: {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                }
            ),
        ])

        return commands
    }

    // MARK: - Recent Chats

    private var recentChatCommands: [PaletteCommand] {
        chatStore.sessions.prefix(5).map { session in
            PaletteCommand(
                id: "recent-chat-\(session.id)",
                title: session.title,
                subtitle: "Resume conversation",
                icon: "clock.arrow.circlepath",
                category: .recent,
                keywords: ["recent", "chat", session.title.lowercased()],
                action: { [session] in
                    Task {
                        await chatStore.selectSession(session)
                        navigationStore.navigate(to: .chat)
                    }
                }
            )
        }
    }

    private var filteredCommands: [PaletteCommand] {
        let commands: [PaletteCommand]

        if searchText.isEmpty {
            commands = allCommands
        } else {
            let query = searchText.lowercased()
            commands = allCommands.filter { command in
                command.title.lowercased().contains(query) ||
                command.subtitle.lowercased().contains(query) ||
                command.keywords.contains(where: { $0.contains(query) })
            }
        }

        // Sort by category order
        return commands.sorted { $0.category.sortOrder < $1.category.sortOrder }
    }

    private var groupedCommands: [PaletteCommandGroup] {
        let grouped = Dictionary(grouping: filteredCommands) { $0.category }
        return grouped
            .map { PaletteCommandGroup(category: $0.key, commands: $0.value) }
            .sorted { $0.category.sortOrder < $1.category.sortOrder }
    }

    private func flatIndex(for command: PaletteCommand) -> Int {
        filteredCommands.firstIndex(where: { $0.id == command.id }) ?? 0
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

            // Keyboard shortcut
            if let shortcut = command.shortcut {
                Text(shortcut)
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundStyle(isSelected ? .white.opacity(0.9) : .secondary)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(isSelected ? Color.white.opacity(0.15) : Color.secondary.opacity(0.08))
                    )
            }

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

// MARK: - Command Section Header

struct CommandSectionHeader: View {
    let title: String

    var body: some View {
        HStack {
            Text(title.uppercased())
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.top, 12)
        .padding(.bottom, 6)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - Palette Command Group

struct PaletteCommandGroup {
    let category: PaletteCommand.CommandCategory
    let commands: [PaletteCommand]
}

// MARK: - Safe Array Subscript

extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

// MARK: - Palette Command Model

struct PaletteCommand: Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let icon: String
    let category: CommandCategory
    let keywords: [String]
    let shortcut: String?
    let action: () -> Void

    init(
        id: String,
        title: String,
        subtitle: String,
        icon: String,
        category: CommandCategory,
        keywords: [String],
        shortcut: String? = nil,
        action: @escaping () -> Void
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.icon = icon
        self.category = category
        self.keywords = keywords
        self.shortcut = shortcut
        self.action = action
    }

    enum CommandCategory: CaseIterable {
        case navigation
        case action
        case window
        case recent
        case tools
        case settings
        case view

        var displayName: String {
            switch self {
            case .navigation: return "Go"
            case .action: return "Create"
            case .window: return "Window"
            case .recent: return "Recent"
            case .tools: return "Tools"
            case .settings: return "Settings"
            case .view: return "View"
            }
        }

        var sortOrder: Int {
            switch self {
            case .recent: return 0
            case .action: return 1
            case .navigation: return 2
            case .window: return 3
            case .tools: return 4
            case .view: return 5
            case .settings: return 6
            }
        }
    }
}
