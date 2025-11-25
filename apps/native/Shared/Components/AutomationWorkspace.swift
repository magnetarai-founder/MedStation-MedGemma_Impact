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
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.bar")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Dashboard")
                .font(.title)

            Text("Starred and recent workflows will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowBuilderView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.and.pencil")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Builder")
                .font(.title)

            Text("Visual workflow canvas will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
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
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Analytics")
                .font(.title)

            Text("Metrics and stage performance will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
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
    @State private var queueItems: [QueueItem] = QueueItem.mockItems

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

    // MARK: - States

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
