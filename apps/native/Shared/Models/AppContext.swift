//
//  AppContext.swift
//  MagnetarStudio
//
//  Unified context across all workspaces for intelligent model routing
//  Part of Noah's Ark for the Digital Age - Cross-app intelligence
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AppContext")

// MARK: - App Context (Unified Cross-Workspace State)

/// Complete application context for intelligent model routing
/// Provides models with awareness of user activity across ALL workspaces
struct AppContext {
    let vault: VaultContext
    let data: DataContext
    let kanban: KanbanContext
    let workflows: WorkflowContext
    let team: TeamContext
    let code: CodeContext  // Future: MagnetarCode integration

    // Cross-workspace memory
    let vectorMemory: ANEContextState
    let modelInteractionHistory: [ModelInteraction]
    let userPreferences: UserPreferences

    // System resource state
    let systemResources: SystemResourceState

    // Timestamp for cache invalidation
    let capturedAt: Date

    /// Get current app context snapshot
    static func current() async -> AppContext {
        async let vault = VaultContext.current()
        async let data = DataContext.current()
        async let kanban = KanbanContext.current()
        async let workflows = WorkflowContext.current()
        async let team = TeamContext.current()
        async let code = CodeContext.current()
        async let vectorMemory = ANEContextState.current()
        async let modelHistory = ModelInteractionHistory.recent(limit: 100)
        async let preferences = UserPreferences.load()
        async let resources = SystemResourceState.current()

        return await AppContext(
            vault: vault,
            data: data,
            kanban: kanban,
            workflows: workflows,
            team: team,
            code: code,
            vectorMemory: vectorMemory,
            modelInteractionHistory: modelHistory,
            userPreferences: preferences,
            systemResources: resources,
            capturedAt: Date()
        )
    }
}

// MARK: - Vault Context

/// Context from Vault workspace (encrypted file storage)
/// SECURITY: Only metadata exposed, file contents require explicit permission
struct VaultContext {
    let unlockedVaultType: String?  // "real" or "decoy" (if unlocked)
    let recentFiles: [VaultFileMetadata]  // Metadata only, NO file contents
    let activePermissions: [FilePermission]  // What files models currently have access to
    let totalFiles: Int
    let totalFolders: Int

    static func current() async -> VaultContext {
        await MainActor.run {
            let store = VaultStore.shared
            let permissionManager = VaultPermissionManager.shared

            return VaultContext(
                unlockedVaultType: store.unlocked ? store.vaultType : nil,
                recentFiles: store.files.prefix(20).map { VaultFileMetadata(from: $0) },
                activePermissions: permissionManager.activePermissions.map { FilePermission(from: $0) },
                totalFiles: store.files.count,
                totalFolders: store.folders.count
            )
        }
    }
}

/// Metadata about a vault file (NO file contents)
struct VaultFileMetadata: Codable {
    let id: String
    let name: String
    let path: String
    let size: Int64?
    let modifiedAt: Date?
    let vaultType: String  // "real" or "decoy"
    let isDirectory: Bool

    init(from file: VaultFile) {
        self.id = file.id
        self.name = file.name
        self.path = file.folderPath ?? "/"
        self.size = Int64(file.size)
        self.modifiedAt = ISO8601DateFormatter().date(from: file.uploadedAt)
        // Note: vaultType must be set by caller via MainActor
        self.vaultType = "real"  // Default, will be overridden
        self.isDirectory = file.isFolder
    }

    init(id: String, name: String, path: String, size: Int64?, modifiedAt: Date?, vaultType: String, isDirectory: Bool) {
        self.id = id
        self.name = name
        self.path = path
        self.size = size
        self.modifiedAt = modifiedAt
        self.vaultType = vaultType
        self.isDirectory = isDirectory
    }
}

/// Active file permission (what models can currently access)
struct FilePermission: Codable, Identifiable {
    let id: UUID
    let fileId: String
    let fileName: String
    let vaultType: String
    let modelId: String
    let grantedAt: Date
    let expiresAt: Date?  // nil = "just this time" (already expired), Date = "for this session"
    let sessionId: String  // Chat session that requested access

    init(from permission: VaultFilePermission) {
        self.id = permission.id
        self.fileId = permission.fileId
        self.fileName = permission.fileName
        self.vaultType = permission.vaultType
        self.modelId = permission.modelId
        self.grantedAt = permission.grantedAt
        self.expiresAt = permission.expiresAt
        self.sessionId = permission.sessionId
    }
}

// MARK: - Data Context

/// Context from Data workspace (SQL queries, databases)
struct DataContext {
    let loadedTables: [TableMetadata]
    let recentQueries: [RecentQuery]
    let activeConnections: [DatabaseConnection]

    static func current() async -> DataContext {
        await MainActor.run {
            let store = DatabaseStore.shared

            // Get table metadata from current file if available
            var tables: [TableMetadata] = []
            if let currentFile = store.currentFile {
                tables.append(TableMetadata(
                    name: currentFile.filename,
                    rowCount: currentFile.rowCount,
                    columns: currentFile.columns.map { col in
                        DataColumnInfo(name: col.originalName, type: col.dtype)
                    },
                    source: "uploaded"
                ))
            }

            // Get recent queries from history (we'll fetch asynchronously)
            var queries: [RecentQuery] = []
            // Note: fetchHistory is async, so we'd need to call it separately
            // For now, if a query has been executed, include it
            if store.hasExecuted, let currentQuery = store.currentQuery {
                queries.append(RecentQuery(
                    sql: store.editorText,
                    executedAt: Date(),
                    success: true,
                    rowsReturned: currentQuery.rowCount
                ))
            }

            // No external connections tracked yet
            let connections: [DatabaseConnection] = []

            return DataContext(
                loadedTables: tables,
                recentQueries: queries,
                activeConnections: connections
            )
        }
    }
}

struct TableMetadata: Codable {
    let name: String
    let rowCount: Int?
    let columns: [DataColumnInfo]
    let source: String  // "uploaded", "connected"
}

struct DataColumnInfo: Codable {
    let name: String
    let type: String
}

struct RecentQuery: Codable {
    let sql: String
    let executedAt: Date
    let success: Bool
    let rowsReturned: Int?
}

struct DatabaseConnection: Codable {
    let name: String
    let type: String  // "postgresql", "mysql", "sqlite"
    let connected: Bool
}

// MARK: - Kanban Context

/// Context from Kanban workspace (task management)
struct KanbanContext {
    let activeBoard: String?
    let activeTasks: [TaskSummary]
    let recentActivity: [KanbanActivity]

    static func current() async -> KanbanContext {
        do {
            // Note: Using default project ID - in production this should be user-selected
            let defaultProjectId = "default"

            // Fetch boards from backend
            let boards = try await KanbanService.shared.listBoards(projectId: defaultProjectId)

            guard let firstBoard = boards.first else {
                // No boards yet
                return KanbanContext(
                    activeBoard: nil,
                    activeTasks: [],
                    recentActivity: []
                )
            }

            // Fetch tasks for the first board
            let tasks = try await KanbanService.shared.listTasks(boardId: firstBoard.boardId)

            // Map to TaskSummary using extension init
            let taskSummaries = tasks.map { TaskSummary(from: $0) }

            return KanbanContext(
                activeBoard: firstBoard.name,
                activeTasks: taskSummaries,
                recentActivity: []  // Activity tracking not implemented yet
            )
        } catch {
            // If backend unavailable, return empty context
            logger.debug("Failed to fetch Kanban context: \(error)")
            return KanbanContext(
                activeBoard: nil,
                activeTasks: [],
                recentActivity: []
            )
        }
    }
}

struct TaskSummary: Codable {
    let id: String
    let title: String
    let status: String
    let priority: String?
    let assignedTo: String?
    let dueDate: Date?
}

struct KanbanActivity: Codable {
    let action: String
    let taskTitle: String
    let timestamp: Date
}

// MARK: - Workflow Context

/// Context from Workflows workspace (automations)
struct WorkflowContext {
    let activeWorkflows: [WorkflowSummary]
    let recentExecutions: [WorkflowExecution]

    static func current() async -> WorkflowContext {
        let store = await MainActor.run { WorkflowStore.shared }
        let executions = await WorkflowExecutionHistory.recent(limit: 10)

        return await MainActor.run {
            WorkflowContext(
                activeWorkflows: store.workflows.prefix(10).map { WorkflowSummary(from: $0) },
                recentExecutions: executions
            )
        }
    }
}

struct WorkflowSummary: Codable {
    let id: String
    let name: String
    let status: String
    let lastRun: Date?
}

struct WorkflowExecution: Codable, Identifiable {
    let id: UUID
    let workflowId: String
    let workflowName: String?
    let startedAt: Date
    let completedAt: Date?
    let success: Bool
    let itemsProcessed: Int?
    let errorMessage: String?

    init(id: UUID = UUID(), workflowId: String, workflowName: String? = nil, startedAt: Date = Date(), completedAt: Date? = nil, success: Bool, itemsProcessed: Int? = nil, errorMessage: String? = nil) {
        self.id = id
        self.workflowId = workflowId
        self.workflowName = workflowName
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.success = success
        self.itemsProcessed = itemsProcessed
        self.errorMessage = errorMessage
    }
}

@MainActor
class WorkflowExecutionHistory {
    private static let storageKey = "workflowExecutionHistory"
    private static let maxStoredExecutions = 500

    static func recent(limit: Int) async -> [WorkflowExecution] {
        guard let data = UserDefaults.standard.data(forKey: storageKey) else {
            return []
        }

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let executions = try decoder.decode(Array<WorkflowExecution>.self, from: data)

            // Return most recent first
            return Array(executions
                .sorted { $0.startedAt > $1.startedAt }
                .prefix(limit))
        } catch {
            logger.error("Failed to load workflow execution history: \(error)")
            return []
        }
    }

    static func record(_ execution: WorkflowExecution) {
        Task { @MainActor in
            // Load existing
            var executions = await recent(limit: maxStoredExecutions)

            // Add new execution
            executions.insert(execution, at: 0)

            // Keep only recent ones
            if executions.count > maxStoredExecutions {
                executions = Array(executions.prefix(maxStoredExecutions))
            }

            // Save
            do {
                let encoder = JSONEncoder()
                encoder.dateEncodingStrategy = .iso8601
                let data = try encoder.encode(executions)
                UserDefaults.standard.set(data, forKey: storageKey)
            } catch {
                logger.error("Failed to save workflow execution history: \(error)")
            }
        }
    }

    /// Get executions for a specific workflow
    static func forWorkflow(_ workflowId: String, limit: Int = 10) async -> [WorkflowExecution] {
        let all = await recent(limit: maxStoredExecutions)
        return Array(all
            .filter { $0.workflowId == workflowId }
            .prefix(limit))
    }

    /// Clear all execution history
    static func clear() {
        UserDefaults.standard.removeObject(forKey: storageKey)
    }
}

// MARK: - Team Context

/// Context from Team workspace (chat, channels)
struct TeamContext {
    let activeChannel: String?
    let recentMessages: [TeamMessageSummary]
    let onlineMembers: Int

    static func current() async -> TeamContext {
        do {
            // Fetch recent documents from team workspace
            let documents = try await TeamService.shared.listDocuments()

            // Convert documents to message summaries for context
            // (Team workspace is document-based, not channel-based currently)
            let messageSummaries = documents.prefix(10).map { doc in
                // Convert updatedAt string to Date
                let formatter = ISO8601DateFormatter()
                let timestamp = formatter.date(from: doc.updatedAt) ?? Date()

                // Get content preview
                let contentStr: String
                if let content = doc.content {
                    contentStr = String(describing: content).prefix(100) + "..."
                } else {
                    contentStr = ""
                }

                return TeamMessageSummary(
                    channelName: "Documents",
                    sender: doc.createdBy,
                    preview: "\(doc.title): \(contentStr)",
                    timestamp: timestamp
                )
            }

            return TeamContext(
                activeChannel: documents.isEmpty ? nil : "Documents",
                recentMessages: messageSummaries,
                onlineMembers: 0  // Online presence not implemented yet
            )
        } catch {
            // If backend unavailable, return empty context
            logger.debug("Failed to fetch Team context: \(error)")
            return TeamContext(
                activeChannel: nil,
                recentMessages: [],
                onlineMembers: 0
            )
        }
    }
}

struct TeamMessageSummary: Codable {
    let channelName: String
    let sender: String
    let preview: String  // First 100 chars
    let timestamp: Date
}

// MARK: - Code Context (Future: MagnetarCode)

/// Context from Code workspace (future integration)
struct CodeContext {
    let openFiles: [String]
    let recentEdits: [CodeEdit]
    let gitBranch: String?

    static func current() async -> CodeContext {
        // Future: MagnetarCode integration
        return CodeContext(
            openFiles: [],
            recentEdits: [],
            gitBranch: nil
        )
    }
}

struct CodeEdit: Codable {
    let filePath: String
    let timestamp: Date
}

// MARK: - ANE Context State

/// State of ANE (Apple Neural Engine) context vectorization
/// Backend Python service provides cross-workspace semantic search
struct ANEContextState {
    let available: Bool
    let indexedDocuments: Int
    let lastIndexedAt: Date?
    let queueDepth: Int
    let features: ANEFeatures

    struct ANEFeatures {
        let semanticSearch: Bool
        let aneAcceleration: Bool
        let backgroundVectorization: Bool

        static let unavailable = ANEFeatures(
            semanticSearch: false,
            aneAcceleration: false,
            backgroundVectorization: false
        )
    }

    static func current() async -> ANEContextState {
        // Query backend ANE Context Engine at /api/v1/context/status
        guard let url = URL(string: APIConfiguration.shared.contextStatusURL) else {
            return .unavailable
        }

        do {
            let (data, response) = try await URLSession.shared.data(from: url)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return .unavailable
            }

            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]

            let available = json["available"] as? Bool ?? false
            let vectorCount = json["vector_count"] as? Int ?? 0
            let queueDepth = json["queue_depth"] as? Int ?? 0

            // Parse features
            let featuresDict = json["features"] as? [String: Any] ?? [:]
            let features = ANEFeatures(
                semanticSearch: featuresDict["semantic_search"] as? Bool ?? false,
                aneAcceleration: featuresDict["ane_acceleration"] as? Bool ?? false,
                backgroundVectorization: featuresDict["background_vectorization"] as? Bool ?? false
            )

            return ANEContextState(
                available: available,
                indexedDocuments: vectorCount,
                lastIndexedAt: Date(),  // Backend doesn't track this, use current time
                queueDepth: queueDepth,
                features: features
            )
        } catch {
            logger.debug("Failed to fetch ANE context status: \(error)")
            return .unavailable
        }
    }

    static let unavailable = ANEContextState(
        available: false,
        indexedDocuments: 0,
        lastIndexedAt: nil,
        queueDepth: 0,
        features: .unavailable
    )
}

// MARK: - Model Interaction History

/// Track what models have done (for learning user patterns)
struct ModelInteraction: Codable, Identifiable {
    let id: UUID
    let modelId: String
    let workspaceType: String  // "vault", "data", "kanban", etc.
    let actionType: String  // "file_access", "query", "code_edit", etc.
    let resourceId: String?  // File ID, query ID, etc.
    let timestamp: Date
    let success: Bool

    init(id: UUID = UUID(), modelId: String, workspaceType: String, actionType: String, resourceId: String? = nil, timestamp: Date = Date(), success: Bool) {
        self.id = id
        self.modelId = modelId
        self.workspaceType = workspaceType
        self.actionType = actionType
        self.resourceId = resourceId
        self.timestamp = timestamp
        self.success = success
    }
}

@MainActor
class ModelInteractionHistory {
    private static let storageKey = "modelInteractionHistory"
    private static let maxStoredInteractions = 1000

    static func recent(limit: Int) async -> [ModelInteraction] {
        guard let data = UserDefaults.standard.data(forKey: storageKey) else {
            return []
        }

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let interactions = try decoder.decode(Array<ModelInteraction>.self, from: data)

            // Return most recent first
            return Array(interactions
                .sorted { $0.timestamp > $1.timestamp }
                .prefix(limit))
        } catch {
            logger.error("Failed to load interaction history: \(error)")
            return []
        }
    }

    static func record(_ interaction: ModelInteraction) {
        Task { @MainActor in
            // Load existing
            var interactions = await recent(limit: maxStoredInteractions)

            // Add new interaction
            interactions.insert(interaction, at: 0)

            // Keep only recent ones
            if interactions.count > maxStoredInteractions {
                interactions = Array(interactions.prefix(maxStoredInteractions))
            }

            // Save
            do {
                let encoder = JSONEncoder()
                encoder.dateEncodingStrategy = .iso8601
                let data = try encoder.encode(interactions)
                UserDefaults.standard.set(data, forKey: storageKey)
            } catch {
                logger.error("Failed to save interaction history: \(error)")
            }
        }
    }

    /// Clear all interaction history
    static func clear() {
        UserDefaults.standard.removeObject(forKey: storageKey)
    }
}

// MARK: - User Preferences

/// User preferences for model behavior
struct UserPreferences: Codable {
    let preferredModels: [String: String]  // Task type -> Model ID
    let alwaysAllowFiles: [String]  // File IDs that don't require permission prompt
    let pinnedHotSlots: [Int]  // Which hot slots are pinned (cannot evict)
    let immutableModels: Bool  // If true, pinned models cannot be unpinned without confirmation
    let askBeforeUnpinning: Bool  // Show modal before unpinning

    private static let storageKey = "userPreferences"

    static func load() async -> UserPreferences {
        guard let data = UserDefaults.standard.data(forKey: storageKey) else {
            // Return defaults if no saved preferences
            return defaultPreferences()
        }

        do {
            let decoder = JSONDecoder()
            return try decoder.decode(UserPreferences.self, from: data)
        } catch {
            logger.error("Failed to load user preferences: \(error)")
            return defaultPreferences()
        }
    }

    static func save(_ preferences: UserPreferences) {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(preferences)
            UserDefaults.standard.set(data, forKey: storageKey)
            logger.debug("Saved user preferences")
        } catch {
            logger.error("Failed to save user preferences: \(error)")
        }
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: storageKey)
    }

    private static func defaultPreferences() -> UserPreferences {
        return UserPreferences(
            preferredModels: [:],
            alwaysAllowFiles: [],
            pinnedHotSlots: [],
            immutableModels: false,
            askBeforeUnpinning: true
        )
    }

    /// Update preferred model for a task type
    func setPreferredModel(_ modelId: String, for taskType: String) -> UserPreferences {
        var models = preferredModels
        models[taskType] = modelId
        return UserPreferences(
            preferredModels: models,
            alwaysAllowFiles: alwaysAllowFiles,
            pinnedHotSlots: pinnedHotSlots,
            immutableModels: immutableModels,
            askBeforeUnpinning: askBeforeUnpinning
        )
    }

    /// Add file to always-allow list
    func allowFile(_ fileId: String) -> UserPreferences {
        var files = alwaysAllowFiles
        if !files.contains(fileId) {
            files.append(fileId)
        }
        return UserPreferences(
            preferredModels: preferredModels,
            alwaysAllowFiles: files,
            pinnedHotSlots: pinnedHotSlots,
            immutableModels: immutableModels,
            askBeforeUnpinning: askBeforeUnpinning
        )
    }

    /// Toggle hot slot pin
    func toggleHotSlotPin(_ slotNumber: Int) -> UserPreferences {
        var pins = pinnedHotSlots
        if let index = pins.firstIndex(of: slotNumber) {
            pins.remove(at: index)
        } else {
            pins.append(slotNumber)
        }
        return UserPreferences(
            preferredModels: preferredModels,
            alwaysAllowFiles: alwaysAllowFiles,
            pinnedHotSlots: pins.sorted(),
            immutableModels: immutableModels,
            askBeforeUnpinning: askBeforeUnpinning
        )
    }
}

// MARK: - System Resource State

/// Current system resource state (prevent crashes/overload)
struct SystemResourceState: Codable {
    let memoryPressure: Float  // 0.0-1.0
    let thermalState: ThermalState
    let activeModels: [LoadedModel]
    let availableMemoryGB: Float
    let cpuUsage: Float  // 0.0-1.0

    static func current() async -> SystemResourceState {
        let processInfo = ProcessInfo.processInfo

        // Get thermal state
        let thermal = ThermalState(from: processInfo.thermalState)

        // Get memory info
        var info = mach_task_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<mach_task_basic_info>.size) / 4
        let result = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: 1) {
                task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), $0, &count)
            }
        }

        let usedMemoryGB = result == KERN_SUCCESS ? Float(info.resident_size) / (1024 * 1024 * 1024) : 0
        let totalMemoryGB = Float(processInfo.physicalMemory) / (1024 * 1024 * 1024)
        let availableMemoryGB = totalMemoryGB - usedMemoryGB

        // Calculate memory pressure (simple heuristic)
        let memoryPressure = min(1.0, usedMemoryGB / totalMemoryGB)

        // Get CPU usage from ResourceMonitor
        let cpuUsage: Float = await MainActor.run {
            ResourceMonitor.shared.getCPUUsage()
        }

        // Get active models from hot slots
        let activeModels = await MainActor.run {
            HotSlotManager.shared.loadedModels()
        }

        return SystemResourceState(
            memoryPressure: memoryPressure,
            thermalState: thermal,
            activeModels: activeModels,
            availableMemoryGB: availableMemoryGB,
            cpuUsage: cpuUsage
        )
    }
}

enum ThermalState: String, Codable {
    case nominal
    case fair
    case serious
    case critical

    init(from state: ProcessInfo.ThermalState) {
        switch state {
        case .nominal: self = .nominal
        case .fair: self = .fair
        case .serious: self = .serious
        case .critical: self = .critical
        @unknown default: self = .nominal
        }
    }
}

struct LoadedModel: Codable, Identifiable {
    let id: String
    let name: String
    let slotNumber: Int
    let memoryUsageGB: Float
    let lastUsedAt: Date
    let isPinned: Bool
}

// MARK: - Helper Extensions

extension WorkflowSummary {
    init(from workflow: Workflow) {
        self.id = workflow.id
        self.name = workflow.name
        self.status = (workflow.enabled ?? true) ? "active" : "disabled"
        self.lastRun = workflow.lastRunAt.flatMap { ISO8601DateFormatter().date(from: $0) }
    }
}

extension TaskSummary {
    init(from task: KanbanTaskAPI) {
        self.id = task.taskId
        self.title = task.title
        self.status = task.status ?? "todo"
        self.priority = task.priority
        self.assignedTo = task.assigneeId
        // Convert dueDate string to Date if present
        if let dueDateStr = task.dueDate {
            self.dueDate = ISO8601DateFormatter().date(from: dueDateStr)
        } else {
            self.dueDate = nil
        }
    }
}

extension TeamMessageSummary {
    init(from message: TeamMessage, channelName: String) {
        self.channelName = channelName
        self.sender = message.senderName
        self.preview = String(message.content.prefix(100))
        self.timestamp = ISO8601DateFormatter().date(from: message.timestamp) ?? Date()
    }
}
