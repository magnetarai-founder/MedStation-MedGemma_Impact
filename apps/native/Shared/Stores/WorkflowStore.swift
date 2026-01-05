import Foundation
import Observation

/// Workflow workspace state and operations
@MainActor
@Observable
final class WorkflowStore {
    static let shared = WorkflowStore()

    // MARK: - State Persistence Keys
    private static let selectedWorkflowIdKey = "workflow.selectedWorkflowId"

    // Persisted workflow ID to restore after workflows load
    @ObservationIgnored
    private var pendingRestoreWorkflowId: String?

    // MARK: - Observable State

    var workflows: [Workflow] = []
    var templates: [Workflow] = []
    var starredIds: Set<String> = []
    var queueItems: [WorkItem] = []
    var myWorkItems: [WorkItem] = []
    var analytics: WorkflowAnalytics?
    var selectedWorkflow: Workflow? {
        didSet { UserDefaults.standard.set(selectedWorkflow?.id, forKey: Self.selectedWorkflowIdKey) }
    }
    var isLoading = false
    var error: String?

    private let service = WorkflowService.shared

    private init() {
        // Store workflow ID to restore after workflows load
        self.pendingRestoreWorkflowId = UserDefaults.standard.string(forKey: Self.selectedWorkflowIdKey)
    }

    /// Restore the previously selected workflow after workflows load
    func restorePersistedWorkflow() {
        guard let workflowId = pendingRestoreWorkflowId else { return }
        if let workflow = workflows.first(where: { $0.id == workflowId }) {
            selectedWorkflow = workflow
        }
        pendingRestoreWorkflowId = nil
    }

    // MARK: - Workflow Management

    func loadWorkflows(type: String = "local") async {
        isLoading = true
        defer { isLoading = false }

        do {
            workflows = try await service.listWorkflows(type: type)
            restorePersistedWorkflow()  // Restore after loading
            error = nil
        } catch {
            self.error = "Failed to load workflows: \(error.localizedDescription)"
        }
    }

    func toggleStar(id: String) async {
        let wasStarred = starredIds.contains(id)

        do {
            if wasStarred {
                try await service.unstarWorkflow(id: id)
                starredIds.remove(id)
            } else {
                try await service.starWorkflow(id: id)
                starredIds.insert(id)
            }
            error = nil
        } catch {
            self.error = "Failed to \(wasStarred ? "unstar" : "star") workflow: \(error.localizedDescription)"
        }
    }

    // MARK: - Templates

    func loadTemplates() async {
        isLoading = true
        defer { isLoading = false }

        do {
            templates = try await service.listTemplates()
            error = nil
        } catch {
            self.error = "Failed to load templates: \(error.localizedDescription)"
        }
    }

    func instantiateTemplate(
        templateId: String,
        name: String,
        description: String? = nil
    ) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newWorkflow = try await service.instantiateTemplate(
                id: templateId,
                name: name,
                description: description
            )

            workflows.insert(newWorkflow, at: 0)
            selectedWorkflow = newWorkflow
            error = nil
        } catch {
            self.error = "Failed to instantiate template: \(error.localizedDescription)"
        }
    }

    // MARK: - Work Items / Queue

    func loadQueue(workflowId: String, role: String? = nil) async {
        isLoading = true
        defer { isLoading = false }

        do {
            queueItems = try await service.getQueue(workflowId: workflowId, role: role)
            error = nil
        } catch {
            self.error = "Failed to load queue: \(error.localizedDescription)"
        }
    }

    func loadMyWork(workflowId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            myWorkItems = try await service.getMyWork(workflowId: workflowId)
            error = nil
        } catch {
            self.error = "Failed to load my work: \(error.localizedDescription)"
        }
    }

    func claimAndStart(workItemId: String, userId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            // 1. Claim the work item
            var workItem = try await service.claimWorkItem(id: workItemId, userId: userId)

            // 2. Start the work item
            workItem = try await service.startWorkItem(id: workItemId, userId: userId)

            // 3. Remove from queue
            queueItems.removeAll { $0.id == workItemId }

            // 4. Add to my work
            if !myWorkItems.contains(where: { $0.id == workItemId }) {
                myWorkItems.insert(workItem, at: 0)
            }

            error = nil
        } catch {
            self.error = "Failed to claim and start work item: \(error.localizedDescription)"
        }
    }

    func claimWorkItem(workItemId: String, userId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let workItem = try await service.claimWorkItem(id: workItemId, userId: userId)

            // Remove from queue
            queueItems.removeAll { $0.id == workItemId }

            // Add to my work
            if !myWorkItems.contains(where: { $0.id == workItemId }) {
                myWorkItems.insert(workItem, at: 0)
            }

            error = nil
        } catch {
            self.error = "Failed to claim work item: \(error.localizedDescription)"
        }
    }

    func startWorkItem(workItemId: String, userId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let workItem = try await service.startWorkItem(id: workItemId, userId: userId)

            // Update in my work
            if let index = myWorkItems.firstIndex(where: { $0.id == workItemId }) {
                myWorkItems[index] = workItem
            }

            error = nil
        } catch {
            self.error = "Failed to start work item: \(error.localizedDescription)"
        }
    }

    // MARK: - Builder (Save/Run)

    func saveWorkflow(
        workflowId: String,
        name: String,
        nodes: [WorkflowNode],
        edges: [WorkflowEdge]
    ) async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await service.saveWorkflow(
                workflowId: workflowId,
                name: name,
                nodes: nodes,
                edges: edges
            )
            error = nil
        } catch {
            self.error = "Failed to save workflow: \(error.localizedDescription)"
        }
    }

    func runWorkflow(
        workflowId: String,
        name: String,
        nodes: [WorkflowNode],
        edges: [WorkflowEdge]
    ) async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await service.runWorkflow(
                workflowId: workflowId,
                name: name,
                nodes: nodes,
                edges: edges
            )
            error = nil
        } catch {
            self.error = "Failed to run workflow: \(error.localizedDescription)"
        }
    }

    // MARK: - Analytics

    func loadAnalytics(workflowId: String) async {
        isLoading = true
        defer { isLoading = false }

        do {
            analytics = try await service.fetchAnalytics(workflowId: workflowId)
            error = nil
        } catch {
            self.error = "Failed to load analytics: \(error.localizedDescription)"
        }
    }

    // MARK: - Helpers

    /// Group work items by stage for status tracking
    func workItemsByStage(items: [WorkItem]) -> [String: [WorkItem]] {
        Dictionary(grouping: items) { $0.currentStageId }
    }

    /// Get starred workflows
    var starredWorkflows: [Workflow] {
        workflows.filter { starredIds.contains($0.id) }
    }

    /// Get workflows by category
    func workflows(byCategory category: String) -> [Workflow] {
        workflows.filter { $0.category == category }
    }
}
