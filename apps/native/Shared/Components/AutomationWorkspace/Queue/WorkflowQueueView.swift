//
//  WorkflowQueueView.swift
//  MagnetarStudio
//
//  Main queue view showing available and active work items
//

import SwiftUI

struct WorkflowQueueView: View {
    @State private var viewMode: QueueViewMode = .available
    @State private var priorityFilter: PriorityFilter = .all
    @State private var isLoading: Bool = false
    @State private var queueItems: [QueueItem] = []
    @State private var selectedWorkflowId: String? = nil
    @State private var errorMessage: String? = nil

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
                let workflowStore = WorkflowStore.shared
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

        // Format timestamp
        let formattedTimestamp = formatTimestamp(workItem.createdAt)

        return QueueItem(
            reference: workItem.referenceNumber ?? "WRK-\(workItem.id.prefix(6))",
            workflowName: workItem.workflowName ?? workflowName,
            stageName: workItem.currentStageName ?? "Unknown Stage",
            priority: priority,
            statusLabels: statusLabels,
            dataPreview: Array(dataPreview),
            createdAt: formattedTimestamp,
            tags: workItem.tags ?? [],
            assignedTo: nil, // TODO: Add assignee field to WorkItem model
            isAssignedToMe: workItem.status == "claimed"
        )
    }

    private func formatTimestamp(_ isoString: String?) -> String {
        guard let isoString = isoString else { return "Recently" }

        // Parse ISO8601 timestamp
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        guard let date = formatter.date(from: isoString) else {
            // Try without fractional seconds
            formatter.formatOptions = [.withInternetDateTime]
            guard let date = formatter.date(from: isoString) else {
                return "Recently"
            }
            return formatRelativeTime(date)
        }

        return formatRelativeTime(date)
    }

    private func formatRelativeTime(_ date: Date) -> String {
        let now = Date()
        let interval = now.timeIntervalSince(date)

        // Less than 1 minute
        if interval < 60 {
            return "Just now"
        }

        // Less than 1 hour
        if interval < 3600 {
            let minutes = Int(interval / 60)
            return "\(minutes)m ago"
        }

        // Less than 24 hours
        if interval < 86400 {
            let hours = Int(interval / 3600)
            return "\(hours)h ago"
        }

        // Less than 7 days
        if interval < 604800 {
            let days = Int(interval / 86400)
            return "\(days)d ago"
        }

        // Use date formatter for older dates
        let dateFormatter = DateFormatter()
        dateFormatter.dateStyle = .short
        dateFormatter.timeStyle = .none
        return dateFormatter.string(from: date)
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
