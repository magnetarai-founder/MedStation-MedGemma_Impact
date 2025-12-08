//
//  AutomationWorkspace.swift
//  MagnetarStudio
//
//  Workflows and automation workspace matching React specs
//  - Tabbed layout: Queue, Dashboard, Builder, Designer, Analytics
//  - Each view has specific toolbar and content matching React files
//

import SwiftUI

struct AutomationWorkspaceView: View {
    @State private var selectedView: WorkflowView = .queue
    @State private var searchText: String = ""

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

            // Content
            contentArea
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // View tabs
            HStack(spacing: 4) {
                ForEach(WorkflowView.allCases, id: \.self) { view in
                    WorkflowTabButton(
                        title: view.displayName,
                        icon: view.icon,
                        isActive: selectedView == view,
                        action: { selectedView = view }
                    )
                }
            }

            Spacer()

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                TextField("Search workflows...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color.gray.opacity(0.1))
            )
            .frame(width: 240)

            // New workflow button
            Button {
                // Create new workflow
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "plus")
                        .font(.system(size: 16))
                    Text("New Workflow")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        switch selectedView {
        case .queue:
            WorkflowQueueView()
        case .dashboard:
            WorkflowDashboardView()
        case .builder:
            WorkflowBuilderView()
        case .designer:
            WorkflowDesignerView()
        case .analytics:
            WorkflowAnalyticsView()
        }
    }
}

// MARK: - Workflow Tab Button

struct WorkflowTabButton: View {
    let title: String
    let icon: String
    let isActive: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                Text(title)
                    .font(.system(size: 14, weight: isActive ? .medium : .regular))
            }
            .foregroundColor(isActive ? Color.magnetarPrimary : (isHovered ? .primary : .secondary))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Workflow Views (Placeholders with proper structure)
// WorkflowQueueView is now in WorkflowQueue.swift

struct WorkflowDashboardView: View {
    @State private var scopeFilter: DashboardScope = .all
    @State private var starredWorkflows: [WorkflowCard] = []
    @State private var recentWorkflows: [WorkflowCard] = []
    @State private var isLoading: Bool = false
    @State private var error: String? = nil

    private let workflowService = WorkflowService.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Scope filter + count
                HStack(spacing: 12) {
                    Menu {
                        Button("All Workflows") { scopeFilter = .all }
                        Button("My Workflows") { scopeFilter = .my }
                        Button("Team Workflows") { scopeFilter = .team }
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "line.3.horizontal.decrease.circle")
                                .font(.system(size: 16))

                            Text(scopeFilter.displayName)
                                .font(.system(size: 14))

                            Image(systemName: "chevron.down")
                                .font(.system(size: 10))
                        }
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.gray.opacity(0.1))
                        )
                    }
                    .buttonStyle(.plain)

                    Text("\(starredWorkflows.count + recentWorkflows.count) workflows")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)

                    Spacer()

                    // Action buttons
                    HStack(spacing: 8) {
                        Button {
                            // Browse templates
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "doc.text.magnifyingglass")
                                    .font(.system(size: 16))
                                Text("Browse Templates")
                                    .font(.system(size: 14, weight: .medium))
                            }
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.orange)
                            )
                        }
                        .buttonStyle(.plain)

                        Button {
                            // Create workflow
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "plus")
                                    .font(.system(size: 16))
                                Text("Create")
                                    .font(.system(size: 14, weight: .medium))
                            }
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.magnetarPrimary)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // Starred section
                if !starredWorkflows.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Image(systemName: "star.fill")
                                .font(.system(size: 16))
                                .foregroundColor(.orange)
                            Text("Starred")
                                .font(.system(size: 18, weight: .semibold))
                        }
                        .padding(.horizontal, 16)

                        WorkflowGrid(workflows: starredWorkflows, showStarByDefault: true)
                    }
                }

                // Agent CTA card
                AgentAssistCard()
                    .padding(.horizontal, 16)

                // Recent section
                if !recentWorkflows.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Image(systemName: "clock")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                            Text("Recent")
                                .font(.system(size: 18, weight: .semibold))
                        }
                        .padding(.horizontal, 16)

                        WorkflowGrid(workflows: recentWorkflows, showStarByDefault: false)
                    }
                }
            }
            .padding(.bottom, 24)
        }
        .task {
            await loadWorkflows()
        }
    }

    // MARK: - Data Loading

    @MainActor
    private func loadWorkflows() async {
        isLoading = true
        error = nil

        do {
            // Load workflows from backend
            let allWorkflows = try await workflowService.listWorkflows(type: "all")

            // Convert Workflow models to WorkflowCard models
            // For now, show all as "recent" until we have starred/favoriting logic
            recentWorkflows = allWorkflows.map { workflow in
                WorkflowCard(
                    name: workflow.name,
                    description: workflow.description ?? "",
                    icon: workflow.icon ?? "gearshape.2",
                    typeName: workflow.category ?? workflow.workflowType ?? "General",
                    typeColor: colorForCategory(workflow.category ?? "general"),
                    isTemplate: workflow.isTemplate ?? false,
                    visibility: visibilityFromString(workflow.visibility ?? "private")
                )
            }

            // For now, starred is empty - would need backend support for favoriting
            starredWorkflows = []
        } catch {
            print("Failed to load workflows: \(error)")
            self.error = "Failed to load workflows"
            // Keep empty arrays on error
        }

        isLoading = false
    }

    // Helper functions
    private func colorForCategory(_ category: String) -> Color {
        switch category.lowercased() {
        case "onboarding": return .green
        case "finance": return .blue
        case "support": return .orange
        case "data": return .purple
        case "content": return .pink
        case "security": return .red
        case "devops": return .cyan
        default: return .blue
        }
    }

    private func visibilityFromString(_ visibility: String) -> WorkflowVisibility {
        switch visibility.lowercased() {
        case "personal", "private": return .private
        case "team": return .team
        case "global", "public": return .public
        default: return .private
        }
    }
}

// MARK: - Workflow Grid

struct WorkflowGrid: View {
    let workflows: [WorkflowCard]
    let showStarByDefault: Bool

    var body: some View {
        LazyVGrid(columns: gridColumns, spacing: 16) {
            ForEach(workflows) { workflow in
                WorkflowCardView(workflow: workflow, showStarByDefault: showStarByDefault)
            }
        }
        .padding(.horizontal, 16)
    }

    private var gridColumns: [GridItem] {
        [GridItem(.adaptive(minimum: 280, maximum: 360), spacing: 16)]
    }
}

// MARK: - Workflow Card

struct WorkflowCardView: View {
    let workflow: WorkflowCard
    let showStarByDefault: Bool
    @State private var isHovered = false
    @State private var isStarred = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Icon chip + Star
            HStack {
                // Icon chip
                HStack(spacing: 6) {
                    Image(systemName: workflow.icon)
                        .font(.system(size: 14))
                        .foregroundColor(workflow.typeColor)

                    Text(workflow.typeName)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(workflow.typeColor)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(workflow.typeColor.opacity(0.15))
                )

                Spacer()

                // Star toggle
                if showStarByDefault || isHovered {
                    Button {
                        isStarred.toggle()
                    } label: {
                        Image(systemName: isStarred ? "star.fill" : "star")
                            .font(.system(size: 16))
                            .foregroundColor(isStarred ? .orange : .secondary)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Title
            Text(workflow.name)
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(.textPrimary)

            // Template badge
            if workflow.isTemplate {
                Text("TEMPLATE")
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundColor(.purple)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.purple.opacity(0.15))
                    )
            }

            // Description
            Text(workflow.description)
                .font(.system(size: 13))
                .foregroundColor(.secondary)
                .lineLimit(2)

            // Visibility badge
            HStack(spacing: 4) {
                Image(systemName: workflow.visibility.icon)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)

                Text(workflow.visibility.displayName)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(isHovered ? 0.1 : 0.05), radius: isHovered ? 8 : 4, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(isHovered ? 0.3 : 0.15), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Agent Assist Card

struct AgentAssistCard: View {
    var body: some View {
        HStack(spacing: 16) {
            // Icon
            ZStack {
                Circle()
                    .fill(Color.purple.opacity(0.15))
                    .frame(width: 48, height: 48)

                Image(systemName: "wand.and.stars")
                    .font(.system(size: 24))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.purple, .pink, .orange],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Workflow Agent Assist")
                    .font(.system(size: 16, weight: .semibold))

                Text("Let AI help you build, optimize, and maintain workflows automatically")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
            }

            Spacer()

            HStack(spacing: 8) {
                Button {
                    // Browse templates
                } label: {
                    Text("Browse Templates")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(Color.orange)
                        )
                }
                .buttonStyle(.plain)

                Button {
                    // Learn more
                } label: {
                    Text("Learn About Agent Assist")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.purple)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .strokeBorder(Color.purple, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.purple.opacity(0.05),
                            Color.pink.opacity(0.05),
                            Color.orange.opacity(0.05)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(
                    LinearGradient(
                        colors: [.purple, .pink, .orange],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        )
    }
}

// MARK: - Dashboard Models

enum DashboardScope: String {
    case all = "All Workflows"
    case my = "My Workflows"
    case team = "Team Workflows"

    var displayName: String { rawValue }
}

enum WorkflowVisibility {
    case `private`
    case team
    case `public`

    var icon: String {
        switch self {
        case .private: return "lock.fill"
        case .team: return "person.2.fill"
        case .public: return "globe"
        }
    }

    var displayName: String {
        switch self {
        case .private: return "Private"
        case .team: return "Team"
        case .public: return "Public"
        }
    }
}

struct WorkflowCard: Identifiable {
    let id = UUID()
    let name: String
    let description: String
    let icon: String
    let typeName: String
    let typeColor: Color
    let isTemplate: Bool
    let visibility: WorkflowVisibility

    static let mockStarred = [
        WorkflowCard(
            name: "Customer Onboarding",
            description: "Automated workflow for onboarding new customers with identity verification and account setup",
            icon: "person.badge.plus",
            typeName: "Onboarding",
            typeColor: .green,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Invoice Processing",
            description: "Extract data from invoices, validate amounts, and route for approval",
            icon: "doc.text",
            typeName: "Finance",
            typeColor: .blue,
            isTemplate: false,
            visibility: .private
        ),
        WorkflowCard(
            name: "Support Ticket Triage",
            description: "Classify incoming support tickets and assign to appropriate teams",
            icon: "ticket",
            typeName: "Support",
            typeColor: .orange,
            isTemplate: true,
            visibility: .public
        )
    ]

    static let mockRecent = [
        WorkflowCard(
            name: "Data Pipeline ETL",
            description: "Extract, transform, and load data from multiple sources into data warehouse",
            icon: "arrow.triangle.branch",
            typeName: "Data",
            typeColor: .purple,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Content Publication",
            description: "Review, approve, and publish content across multiple channels",
            icon: "doc.richtext",
            typeName: "Content",
            typeColor: .pink,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Security Incident Response",
            description: "Automated playbook for security incident detection, analysis, and remediation",
            icon: "shield",
            typeName: "Security",
            typeColor: .red,
            isTemplate: true,
            visibility: .public
        ),
        WorkflowCard(
            name: "Code Review Automation",
            description: "Automated code quality checks, test execution, and PR review routing",
            icon: "chevron.left.forwardslash.chevron.right",
            typeName: "DevOps",
            typeColor: .cyan,
            isTemplate: false,
            visibility: .team
        )
    ]
}

struct WorkflowBuilderView: View {
    @State private var workflowTitle: String = "Customer Onboarding Flow"
    @State private var isEditingTitle: Bool = false
    @State private var isRunning: Bool = false
    @State private var showInfoPanel: Bool = false
    @State private var showHelpPanel: Bool = false
    @State private var isHoveringTitle: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            builderHeader
                .padding(.horizontal, 24)
                .padding(.vertical, 16)
                .background(Color(.controlBackgroundColor))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Canvas with floating controls
            ZStack(alignment: .bottomTrailing) {
                canvasArea

                // Bottom-right: Info controls
                VStack(alignment: .trailing, spacing: 12) {
                    if showInfoPanel {
                        infoPanel
                    }

                    floatingButton(
                        icon: "info.circle",
                        isActive: showInfoPanel,
                        action: { showInfoPanel.toggle() }
                    )
                }
                .padding(.trailing, 20)
                .padding(.bottom, 160)

                // Bottom-left: Help panel
                VStack(alignment: .leading, spacing: 12) {
                    if showHelpPanel {
                        helpPanel
                    }

                    floatingButton(
                        icon: "questionmark.circle",
                        isActive: showHelpPanel,
                        action: { showHelpPanel.toggle() }
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.leading, 24)
                .padding(.bottom, 24)
            }
        }
    }

    // MARK: - Header

    private var builderHeader: some View {
        HStack(spacing: 12) {
            // Back button
            Button {
                // Navigate back
            } label: {
                Image(systemName: "arrow.left")
                    .font(.system(size: 20))
                    .foregroundColor(.primary)
                    .frame(width: 40, height: 40)
            }
            .buttonStyle(.plain)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.0))
            )
            .onHover { hovering in
                // Hover effect
            }

            // Title block
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 8) {
                    if isEditingTitle {
                        TextField("", text: $workflowTitle)
                            .font(.system(size: 20, weight: .semibold))
                            .textFieldStyle(.plain)
                            .overlay(
                                Rectangle()
                                    .fill(Color.magnetarPrimary)
                                    .frame(height: 2),
                                alignment: .bottom
                            )
                            .onSubmit {
                                isEditingTitle = false
                            }
                    } else {
                        Text(workflowTitle)
                            .font(.system(size: 20, weight: .semibold))
                            .onTapGesture {
                                isEditingTitle = true
                            }
                            .onHover { hovering in
                                isHoveringTitle = hovering
                            }

                        if isHoveringTitle {
                            Image(systemName: "pencil")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                        }
                    }
                }

                Text("Drag nodes to customize your workflow")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Right: Save + Run buttons
            HStack(spacing: 8) {
                Button {
                    // Save workflow
                } label: {
                    Image(systemName: "square.and.arrow.down")
                        .font(.system(size: 20))
                        .foregroundColor(.primary)
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )

                Button {
                    isRunning.toggle()
                } label: {
                    Image(systemName: "play.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.white)
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.magnetarPrimary)
                )
                .opacity(isRunning ? 0.6 : 1.0)
                .animation(isRunning ? Animation.easeInOut(duration: 1.0).repeatForever() : .default, value: isRunning)
            }
        }
    }

    // MARK: - Canvas

    private var canvasArea: some View {
        ZStack {
            // Dot background
            DotPattern()

            // Canvas content
            VStack(spacing: 16) {
                Image(systemName: "square.grid.3x2")
                    .font(.system(size: 64))
                    .foregroundColor(.secondary)

                Text("Workflow Canvas")
                    .font(.title)

                Text("ReactFlow-style node editor will render here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            // Minimap (top-right corner)
            VStack {
                HStack {
                    Spacer()

                    VStack(spacing: 8) {
                        Text("MiniMap")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.3))
                            .frame(width: 120, height: 80)
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(.controlBackgroundColor))
                            .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                    .padding(16)
                }

                Spacer()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Floating Controls

    private func floatingButton(icon: String, isActive: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(isActive ? Color.magnetarPrimary : .primary)
                .frame(width: 40, height: 40)
        }
        .buttonStyle(.plain)
        .background(
            Circle()
                .fill(isActive ? Color.magnetarPrimary.opacity(0.1) : Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            Circle()
                .strokeBorder(isActive ? Color.magnetarPrimary.opacity(0.3) : Color.gray.opacity(0.2), lineWidth: 1)
        )
        .scaleEffect(1.0)
        .animation(.easeInOut(duration: 0.2), value: isActive)
    }

    private var infoPanel: some View {
        VStack(spacing: 0) {
            // Header
            Text("Zoom Controls")
                .font(.system(size: 14, weight: .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.gray.opacity(0.03))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Zoom buttons
            VStack(spacing: 0) {
                controlButton(icon: "plus.magnifyingglass", label: "Zoom In")
                controlButton(icon: "minus.magnifyingglass", label: "Zoom Out")
                controlButton(icon: "arrow.up.left.and.arrow.down.right", label: "Fit View")
            }
            .padding(12)
        }
        .frame(width: 200)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    private var helpPanel: some View {
        VStack(spacing: 0) {
            // Header
            Text("Node Types")
                .font(.system(size: 14, weight: .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.gray.opacity(0.03))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Legend items
            VStack(alignment: .leading, spacing: 12) {
                legendRow(color: .green, label: "Trigger")
                legendRow(color: .blue, label: "Action")
                legendRow(color: .purple, label: "AI Stage")
                legendRow(color: .orange, label: "Output")
            }
            .padding(16)
        }
        .frame(width: 280)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    private func controlButton(icon: String, label: String) -> some View {
        Button {
            // Zoom action
        } label: {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(.primary)
                    .frame(width: 20)

                Text(label)
                    .font(.system(size: 14))
                    .foregroundColor(.primary)

                Spacer()
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.clear)
        )
        .onHover { hovering in
            // Hover effect
        }
    }

    private func legendRow(color: Color, label: String) -> some View {
        HStack(spacing: 10) {
            Circle()
                .fill(color)
                .frame(width: 12, height: 12)

            Text(label)
                .font(.system(size: 14))
                .foregroundColor(.secondary)

            Spacer()
        }
    }
}

// MARK: - Dot Pattern Background

struct DotPattern: View {
    let gap: CGFloat = 16
    let dotSize: CGFloat = 1

    var body: some View {
        GeometryReader { geometry in
            Path { path in
                let cols = Int(geometry.size.width / gap)
                let rows = Int(geometry.size.height / gap)

                for row in 0...rows {
                    for col in 0...cols {
                        let x = CGFloat(col) * gap
                        let y = CGFloat(row) * gap
                        path.addEllipse(in: CGRect(x: x - dotSize/2, y: y - dotSize/2, width: dotSize, height: dotSize))
                    }
                }
            }
            .fill(Color.gray.opacity(0.2))
        }
    }
}

struct WorkflowDesignerView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "paintbrush")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Designer")
                .font(.title)

            Text("Stage list and editor will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowAnalyticsView: View {
    @State private var analytics: LegacyWorkflowAnalytics = LegacyWorkflowAnalytics.mock

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Primary metrics grid
                LazyVGrid(columns: metricsColumns, spacing: 16) {
                    MetricCard(
                        title: "Total Items",
                        value: "\(analytics.totalItems)",
                        icon: "square.stack.3d.up",
                        color: .blue
                    )

                    MetricCard(
                        title: "Completed",
                        value: "\(analytics.completedItems)",
                        subtitle: "\(analytics.completionPercent)%",
                        icon: "checkmark.circle.fill",
                        color: .green
                    )

                    MetricCard(
                        title: "In Progress",
                        value: "\(analytics.inProgressItems)",
                        icon: "arrow.triangle.2.circlepath",
                        color: .orange
                    )

                    MetricCard(
                        title: "Avg Cycle Time",
                        value: analytics.avgCycleTime,
                        subtitle: analytics.medianCycleTime != nil ? "Median: \(analytics.medianCycleTime!)" : nil,
                        icon: "clock",
                        color: .purple
                    )
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // Extra status metrics
                if analytics.cancelledItems > 0 || analytics.failedItems > 0 {
                    LazyVGrid(columns: extraMetricsColumns, spacing: 16) {
                        if analytics.cancelledItems > 0 {
                            MetricCard(
                                title: "Cancelled",
                                value: "\(analytics.cancelledItems)",
                                icon: "xmark.circle",
                                color: .gray,
                                isCompact: true
                            )
                        }

                        if analytics.failedItems > 0 {
                            MetricCard(
                                title: "Failed",
                                value: "\(analytics.failedItems)",
                                icon: "exclamationmark.triangle.fill",
                                color: .red,
                                isCompact: true
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                }

                // Stage Performance Table
                VStack(alignment: .leading, spacing: 12) {
                    Text("Stage Performance")
                        .font(.system(size: 18, weight: .semibold))
                        .padding(.horizontal, 16)

                    StagePerformanceTable(stages: analytics.stagePerformance)
                }
            }
            .padding(.bottom, 24)
        }
    }

    private var metricsColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16)
        ]
    }

    private var extraMetricsColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16)
        ]
    }
}

// MARK: - Metric Card

struct MetricCard: View {
    let title: String
    let value: String
    var subtitle: String? = nil
    let icon: String
    let color: Color
    var isCompact: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: isCompact ? 8 : 12) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: isCompact ? 18 : 24))
                    .foregroundColor(color)

                Spacer()

                Text(title)
                    .font(.system(size: isCompact ? 12 : 13))
                    .foregroundColor(.secondary)
                    .textCase(.uppercase)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(value)
                    .font(.system(size: isCompact ? 24 : 32, weight: .bold))
                    .foregroundColor(.textPrimary)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(isCompact ? 12 : 16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(0.15), lineWidth: 1)
        )
    }
}

// MARK: - Stage Performance Table

struct StagePerformanceTable: View {
    let stages: [LegacyStagePerformance]

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 16) {
                Text("Stage")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Entered")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 80, alignment: .trailing)

                Text("Completed")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Avg Time")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Median Time")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 100, alignment: .trailing)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.05))

            Divider()

            // Rows
            ForEach(stages) { stage in
                VStack(spacing: 0) {
                    HStack(spacing: 16) {
                        Text(stage.name)
                            .font(.system(size: 14))
                            .foregroundColor(.textPrimary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        Text("\(stage.entered)")
                            .font(.system(size: 14))
                            .foregroundColor(.textPrimary)
                            .frame(width: 80, alignment: .trailing)

                        Text("\(stage.completed)")
                            .font(.system(size: 14))
                            .foregroundColor(.textPrimary)
                            .frame(width: 100, alignment: .trailing)

                        Text(stage.avgTime)
                            .font(.system(size: 14, design: .monospaced))
                            .foregroundColor(.textPrimary)
                            .frame(width: 100, alignment: .trailing)

                        Text(stage.medianTime ?? "—")
                            .font(.system(size: 14, design: .monospaced))
                            .foregroundColor(stage.medianTime != nil ? .textPrimary : .secondary)
                            .frame(width: 100, alignment: .trailing)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)

                    if stage.id != stages.last?.id {
                        Divider()
                    }
                }
                .background(Color.clear)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.15), lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }
}

// MARK: - Analytics Models

// Legacy mock analytics model used for the UI preview; renamed to avoid clashing with backend model.
struct LegacyWorkflowAnalytics {
    let totalItems: Int
    let completedItems: Int
    let inProgressItems: Int
    let cancelledItems: Int
    let failedItems: Int
    let avgCycleTime: String
    let medianCycleTime: String?
    let stagePerformance: [LegacyStagePerformance]

    var completionPercent: Int {
        guard totalItems > 0 else { return 0 }
        return Int((Double(completedItems) / Double(totalItems)) * 100)
    }

    static let mock = LegacyWorkflowAnalytics(
        totalItems: 1847,
        completedItems: 1523,
        inProgressItems: 287,
        cancelledItems: 24,
        failedItems: 13,
        avgCycleTime: "3.2h",
        medianCycleTime: "2.8h",
        stagePerformance: [
            LegacyStagePerformance(name: "Initial Triage", entered: 1847, completed: 1823, avgTime: "12m", medianTime: "10m"),
            LegacyStagePerformance(name: "Data Validation", entered: 1823, completed: 1789, avgTime: "45m", medianTime: "38m"),
            LegacyStagePerformance(name: "Processing", entered: 1789, completed: 1654, avgTime: "1.8h", medianTime: "1.5h"),
            LegacyStagePerformance(name: "Review", entered: 1654, completed: 1598, avgTime: "2.3h", medianTime: "2.0h"),
            LegacyStagePerformance(name: "Approval", entered: 1598, completed: 1523, avgTime: "4.1h", medianTime: "3.2h")
        ]
    )
}

struct LegacyStagePerformance: Identifiable {
    let id = UUID()
    let name: String
    let entered: Int
    let completed: Int
    let avgTime: String
    let medianTime: String?
}

// MARK: - Supporting Types

enum WorkflowView: String, CaseIterable {
    case queue
    case dashboard
    case builder
    case designer
    case analytics

    var displayName: String {
        switch self {
        case .queue: return "Queue"
        case .dashboard: return "Dashboard"
        case .builder: return "Builder"
        case .designer: return "Designer"
        case .analytics: return "Analytics"
        }
    }

    var icon: String {
        switch self {
        case .queue: return "list.bullet.clipboard"
        case .dashboard: return "chart.bar"
        case .builder: return "square.and.pencil"
        case .designer: return "paintbrush"
        case .analytics: return "chart.line.uptrend.xyaxis"
        }
    }
}

// MARK: - Preview

#Preview {
    AutomationWorkspaceView()
        .frame(width: 1200, height: 800)
}

struct WorkflowQueueView: View {
    @State private var viewMode: QueueViewMode = .available
    @State private var priorityFilter: PriorityFilter = .all
    @State private var isLoading: Bool = false
    @State private var queueItems: [QueueItem] = []
    @State private var selectedWorkflowId: String? = nil
    @State private var errorMessage: String? = nil

    @EnvironmentObject private var workflowStore: WorkflowStore

    var body: some View {
        VStack(spacing: 0) {
            // Header bar
            headerBar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.05))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content
            if isLoading {
                loadingState
            } else if let error = errorMessage {
                errorState(error)
            } else if filteredItems.isEmpty {
                emptyState
            } else {
                ScrollView {
                    LazyVGrid(columns: gridColumns, spacing: 16) {
                        ForEach(filteredItems) { item in
                            QueueItemCard(item: item)
                        }
                    }
                    .padding(16)
                }
            }
        }
        .onAppear {
            loadQueue()
        }
    }

    // MARK: - Header Bar

    private var headerBar: some View {
        HStack(spacing: 12) {
            // Title with emoji
            HStack(spacing: 8) {
                Text(viewMode == .myActive ? "📌" : "📋")
                    .font(.system(size: 20))

                Text(viewMode == .myActive ? "My Active Work" : "Available Queue")
                    .font(.system(size: 16, weight: .semibold))
            }

            Spacer()

            // View toggle
            HStack(spacing: 4) {
                ToggleButton(
                    title: "Available",
                    isActive: viewMode == .available,
                    action: { viewMode = .available }
                )

                ToggleButton(
                    title: "My Active",
                    isActive: viewMode == .myActive,
                    action: { viewMode = .myActive }
                )
            }
            .padding(4)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.1))
            )

            // Priority filter
            Menu {
                Button("All Priorities") { priorityFilter = .all }
                Divider()
                Button("🔴 High") { priorityFilter = .high }
                Button("🟡 Medium") { priorityFilter = .medium }
                Button("🟢 Low") { priorityFilter = .low }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "line.3.horizontal.decrease.circle")
                        .font(.system(size: 16))

                    Text(priorityFilter.displayName)
                        .font(.system(size: 14))

                    Image(systemName: "chevron.down")
                        .font(.system(size: 10))
                }
                .foregroundColor(.secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.gray.opacity(0.1))
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Grid Layout

    private var gridColumns: [GridItem] {
        [GridItem(.adaptive(minimum: 320, maximum: 400), spacing: 16)]
    }

    private var filteredItems: [QueueItem] {
        var items = queueItems

        // Filter by view mode
        if viewMode == .myActive {
            items = items.filter { $0.isAssignedToMe }
        }

        // Filter by priority
        if priorityFilter != .all {
            items = items.filter { $0.priority == priorityFilter.toPriority() }
        }

        return items
    }

    // MARK: - Data Loading

    private func loadQueue() {
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Get the first workflow from the store to load its queue
                // In a full implementation, this would be user-selected
                guard let firstWorkflow = workflowStore.workflows.first else {
                    await MainActor.run {
                        queueItems = []
                        isLoading = false
                    }
                    return
                }

                selectedWorkflowId = firstWorkflow.id

                // Fetch work items based on view mode
                let workItems: [WorkItem]
                if viewMode == .myActive {
                    workItems = try await WorkflowService.shared.getMyWork(workflowId: firstWorkflow.id)
                } else {
                    workItems = try await WorkflowService.shared.getQueue(workflowId: firstWorkflow.id)
                }

                // Convert WorkItems to QueueItems
                let items = workItems.map { workItem in
                    convertToQueueItem(workItem: workItem, workflowName: firstWorkflow.name)
                }

                await MainActor.run {
                    queueItems = items
                    isLoading = false
                }
            } catch {
                print("❌ Failed to load queue: \(error)")
                await MainActor.run {
                    errorMessage = "Failed to load queue: \(error.localizedDescription)"
                    queueItems = []
                    isLoading = false
                }
            }
        }
    }

    private func convertToQueueItem(workItem: WorkItem, workflowName: String) -> QueueItem {
        // Extract data preview from work item data
        let dataPreview = workItem.data.prefix(3).map { (key: $0.key, value: String(describing: $0.value.value)) }

        // Map priority
        let priority: ItemPriority
        switch workItem.priority.lowercased() {
        case "urgent", "high": priority = .high
        case "low": priority = .low
        default: priority = .medium
        }

        // Create status labels from work item status
        let statusLabels = [workItem.status.capitalized]

        return QueueItem(
            reference: workItem.referenceNumber ?? "WRK-\(workItem.id.prefix(6))",
            workflowName: workItem.workflowName ?? workflowName,
            stageName: workItem.currentStageName ?? "Unknown Stage",
            priority: priority,
            statusLabels: statusLabels,
            dataPreview: Array(dataPreview),
            createdAt: "Recently", // TODO: Format timestamp from backend
            tags: [], // TODO: Extract tags from work item data
            assignedTo: nil, // TODO: Add assignee field to WorkItem model
            isAssignedToMe: workItem.status == "claimed"
        )
    }

    // MARK: - States

    private func errorState(_ message: String) -> some View {
        VStack(spacing: 16) {
            Text("⚠️")
                .font(.system(size: 64))

            Text("Error Loading Queue")
                .font(.title2)
                .fontWeight(.semibold)

            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Button("Retry") {
                loadQueue()
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var loadingState: some View {
        VStack(spacing: 16) {
            Text("⏳")
                .font(.system(size: 64))

            Text("Loading queue...")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Fetching available work items")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Text(viewMode == .myActive ? "✅" : "📭")
                .font(.system(size: 64))

            Text(viewMode == .myActive ? "All caught up!" : "No items available")
                .font(.title2)
                .fontWeight(.semibold)

            Text(viewMode == .myActive ? "You have no active work items" : "Check back later for new work")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Queue Item Card

struct QueueItemCard: View {
    let item: QueueItem
    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Priority emoji + Ref pill
            HStack(spacing: 8) {
                Text(item.priority.emoji)
                    .font(.system(size: 20))

                Text(item.reference)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.gray.opacity(0.15))
                    )

                Spacer()
            }

            // Workflow + Stage subtitle
            HStack(spacing: 6) {
                Image(systemName: "arrow.triangle.branch")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                Text(item.workflowName)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.textPrimary)

                Text("→")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                Text(item.stageName)
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
            }

            // Status pills
            HStack(spacing: 6) {
                ForEach(item.statusLabels, id: \.self) { label in
                    StatusPill(text: label)
                }
            }

            // Data preview section
            if !item.dataPreview.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Data Preview")
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundColor(.secondary)
                        .textCase(.uppercase)

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(item.dataPreview.prefix(3), id: \.key) { preview in
                            HStack(spacing: 8) {
                                Text(preview.key)
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)

                                Text(preview.value)
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(.textPrimary)
                            }
                        }
                    }
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.gray.opacity(0.05))
                    )
                }
            }

            // Footer meta
            HStack(spacing: 12) {
                // Created time
                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text(item.createdAt)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                // Tags
                if !item.tags.isEmpty {
                    HStack(spacing: 4) {
                        Image(systemName: "tag")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)

                        Text(item.tags.joined(separator: ", "))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                // Assigned info
                if let assignee = item.assignedTo {
                    HStack(spacing: 4) {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text(assignee)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(isHovered ? 0.1 : 0.05), radius: isHovered ? 8 : 4, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.gray.opacity(isHovered ? 0.3 : 0.15), lineWidth: 1)
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Supporting Components

struct ToggleButton: View {
    let title: String
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: isActive ? .medium : .regular))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                )
        }
        .buttonStyle(.plain)
    }
}

struct StatusPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption2)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(pillColor.opacity(0.2))
            )
            .foregroundColor(pillColor)
    }

    private var pillColor: Color {
        switch text.lowercased() {
        case "pending": return .orange
        case "in progress": return .blue
        case "review": return .purple
        case "blocked": return .red
        case "completed": return .green
        default: return .gray
        }
    }
}

// MARK: - Models

enum QueueViewMode {
    case available
    case myActive
}

enum PriorityFilter: String {
    case all = "All Priorities"
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var displayName: String {
        rawValue
    }

    func toPriority() -> ItemPriority? {
        switch self {
        case .all: return nil
        case .high: return .high
        case .medium: return .medium
        case .low: return .low
        }
    }
}

enum ItemPriority: String {
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var emoji: String {
        switch self {
        case .high: return "🔴"
        case .medium: return "🟡"
        case .low: return "🟢"
        }
    }
}

struct QueueItem: Identifiable {
    let id = UUID()
    let reference: String
    let workflowName: String
    let stageName: String
    let priority: ItemPriority
    let statusLabels: [String]
    let dataPreview: [(key: String, value: String)]
    let createdAt: String
    let tags: [String]
    let assignedTo: String?
    let isAssignedToMe: Bool

    static let mockItems = [
        QueueItem(
            reference: "WRK-1234",
            workflowName: "Customer Onboarding",
            stageName: "Identity Verification",
            priority: .high,
            statusLabels: ["Pending", "Review"],
            dataPreview: [
                (key: "Customer ID", value: "CUST-5678"),
                (key: "Email", value: "alice@example.com"),
                (key: "Status", value: "Documents Uploaded")
            ],
            createdAt: "2h ago",
            tags: ["onboarding", "urgent"],
            assignedTo: "Alice Johnson",
            isAssignedToMe: true
        ),
        QueueItem(
            reference: "WRK-1235",
            workflowName: "Data Processing Pipeline",
            stageName: "Validation",
            priority: .medium,
            statusLabels: ["In Progress"],
            dataPreview: [
                (key: "Batch ID", value: "BATCH-9012"),
                (key: "Records", value: "1,245"),
                (key: "Progress", value: "67%")
            ],
            createdAt: "5h ago",
            tags: ["data", "pipeline"],
            assignedTo: "Bob Smith",
            isAssignedToMe: false
        ),
        QueueItem(
            reference: "WRK-1236",
            workflowName: "Support Ticket Resolution",
            stageName: "Initial Triage",
            priority: .low,
            statusLabels: ["Pending"],
            dataPreview: [
                (key: "Ticket ID", value: "TKT-3456"),
                (key: "Subject", value: "Login Issue"),
                (key: "Customer", value: "Carol Davis")
            ],
            createdAt: "1d ago",
            tags: ["support"],
            assignedTo: nil,
            isAssignedToMe: false
        ),
        QueueItem(
            reference: "WRK-1237",
            workflowName: "Invoice Approval",
            stageName: "Finance Review",
            priority: .high,
            statusLabels: ["Review", "Blocked"],
            dataPreview: [
                (key: "Invoice", value: "INV-7890"),
                (key: "Amount", value: "$12,450.00"),
                (key: "Vendor", value: "Acme Corp")
            ],
            createdAt: "30m ago",
            tags: ["finance", "urgent"],
            assignedTo: "David Wilson",
            isAssignedToMe: true
        ),
        QueueItem(
            reference: "WRK-1238",
            workflowName: "Content Publication",
            stageName: "Editorial Review",
            priority: .medium,
            statusLabels: ["In Progress"],
            dataPreview: [
                (key: "Article ID", value: "ART-1122"),
                (key: "Title", value: "Q4 Product Roadmap"),
                (key: "Author", value: "Eve Martinez")
            ],
            createdAt: "3h ago",
            tags: ["content", "marketing"],
            assignedTo: "Eve Martinez",
            isAssignedToMe: false
        )
    ]
}

// MARK: - Preview

#Preview {
    WorkflowQueueView()
        .frame(width: 1200, height: 800)
}
