//
//  CrossWorkspaceLearning.swift
//  MagnetarStudio
//
//  STUB: Not currently wired — future cross-workspace ML pattern learning.
//  Learns cross-workspace transition patterns for intelligent preloading.
//  Addresses Gap 6: Data→Chat, Code→Chat, Vault→Chat pattern learning.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "CrossWorkspaceLearning")

// MARK: - Cross Workspace Learning

@MainActor
final class CrossWorkspaceLearning: ObservableObject {

    // MARK: - Published State

    @Published private(set) var currentWorkspace: WorkspaceType = .chat
    @Published private(set) var transitionHistory: [WorkspaceTransition] = []

    // MARK: - Dependencies

    private let behaviorTracker: UserBehaviorTracker
    private let contextPreloader: ContextPreloader
    private let storageService: ConversationStorageService

    // MARK: - Learned Patterns

    private var learnedPatterns: [LearnablePattern: PatternStrength] = [:]

    // MARK: - Configuration

    let maxTransitionHistory = 100
    let patternConfidenceThreshold: Float = 0.6

    // MARK: - Singleton

    static let shared = CrossWorkspaceLearning()

    // MARK: - Initialization

    init(
        behaviorTracker: UserBehaviorTracker? = nil,
        contextPreloader: ContextPreloader? = nil,
        storageService: ConversationStorageService? = nil
    ) {
        self.behaviorTracker = behaviorTracker ?? .shared
        self.contextPreloader = contextPreloader ?? .shared
        self.storageService = storageService ?? .shared

        loadPatterns()
    }

    // MARK: - Transition Tracking

    /// Track a workspace transition
    func trackTransition(
        from source: WorkspaceType,
        to destination: WorkspaceType,
        context: TransitionContext
    ) async {
        let transition = WorkspaceTransition(
            from: source,
            to: destination,
            context: context,
            timestamp: Date()
        )

        transitionHistory.append(transition)

        // Prune old history
        if transitionHistory.count > maxTransitionHistory {
            transitionHistory.removeFirst()
        }

        // Record in behavior tracker
        behaviorTracker.trackTabSwitched(from: source.rawValue, to: destination.rawValue)

        // Learn patterns
        updatePatterns(from: transition)

        // Predict and preload
        if let prediction = predictNeededContext(for: destination, given: context) {
            await executePreload(prediction, context: context)
        }

        currentWorkspace = destination
        logger.debug("[CrossWorkspace] Transition: \(source.rawValue) -> \(destination.rawValue)")
    }

    // MARK: - Pattern Learning

    /// Update learned patterns based on transition
    private func updatePatterns(from transition: WorkspaceTransition) {
        let pattern = inferPattern(from: transition)

        if let existingStrength = learnedPatterns[pattern] {
            // Strengthen existing pattern
            learnedPatterns[pattern] = PatternStrength(
                occurrences: existingStrength.occurrences + 1,
                lastSeen: Date(),
                averageConfidence: (existingStrength.averageConfidence + 0.1).clamped(to: 0...1)
            )
        } else {
            // New pattern
            learnedPatterns[pattern] = PatternStrength(
                occurrences: 1,
                lastSeen: Date(),
                averageConfidence: 0.5
            )
        }

        savePatterns()
    }

    /// Infer pattern from transition
    private func inferPattern(from transition: WorkspaceTransition) -> LearnablePattern {
        switch (transition.from, transition.to) {
        case (.data, .chat):
            if let datasetId = transition.context.activeDatasetId {
                return .dataTabThenChat(datasetId: datasetId)
            }
            return .genericTransition(from: .data, to: .chat)

        case (.vault, .chat):
            if let fileId = transition.context.activeFileId {
                return .vaultFileThenChat(fileId: fileId)
            }
            return .genericTransition(from: .vault, to: .chat)

        case (.workflow, .chat):
            if let workflowId = transition.context.activeWorkflowId {
                return .workflowThenChat(workflowId: workflowId)
            }
            return .genericTransition(from: .workflow, to: .chat)

        case (.kanban, .chat):
            if let taskId = transition.context.activeKanbanTaskId {
                return .kanbanThenChat(taskId: taskId)
            }
            return .genericTransition(from: .kanban, to: .chat)

        case (.code, .chat):
            if let filePath = transition.context.activeCodeFilePath {
                return .codeFileThenChat(filePath: filePath)
            }
            return .genericTransition(from: .code, to: .chat)

        case (.team, .chat):
            if let teamId = transition.context.activeTeamId {
                return .teamChatThenMainChat(teamId: teamId)
            }
            return .genericTransition(from: .team, to: .chat)

        case (.hub, .chat):
            if let modelId = transition.context.activeModelId {
                return .huggingFaceDownloadThenChat(modelId: modelId)
            }
            return .genericTransition(from: .hub, to: .chat)

        default:
            return .genericTransition(from: transition.from, to: transition.to)
        }
    }

    // MARK: - Context Prediction

    /// Predict what context will be needed based on transition
    func predictNeededContext(
        for workspace: WorkspaceType,
        given context: TransitionContext
    ) -> ContextPreloadPrediction? {
        switch workspace {
        case .chat:
            return predictChatContext(given: context)

        case .data:
            // In data tab, might need recent data-related conversations
            if let query = context.lastQuery,
               query.lowercased().contains("data") || query.lowercased().contains("query") {
                return .preloadRelevantDatasets(query: query)
            }
            return nil

        case .vault:
            // Preload recently discussed files
            return .preloadRecentlyMentionedFiles

        case .workflow:
            // Preload workflows mentioned in recent chat
            return .preloadDiscussedWorkflows

        case .code:
            // Preload code-related context
            if let filePath = context.activeCodeFilePath {
                return .preloadCodeContext(filePath: filePath)
            }
            return nil

        default:
            return nil
        }
    }

    /// Predict context needed when entering chat
    private func predictChatContext(given context: TransitionContext) -> ContextPreloadPrediction? {
        // Check for specific patterns
        if let datasetId = context.activeDatasetId {
            return .preloadDatasetContext(datasetId: datasetId)
        }

        if let fileId = context.activeFileId {
            return .preloadFileContext(fileId: fileId)
        }

        if let workflowId = context.activeWorkflowId {
            return .preloadWorkflowContext(workflowId: workflowId)
        }

        if let taskId = context.activeKanbanTaskId {
            return .preloadKanbanTaskContext(taskId: taskId)
        }

        if let filePath = context.activeCodeFilePath {
            return .preloadCodeContext(filePath: filePath)
        }

        return nil
    }

    // MARK: - Preload Execution

    /// Execute a preload prediction
    private func executePreload(_ prediction: ContextPreloadPrediction, context: TransitionContext) async {
        guard let sessionId = context.activeSessionId else { return }

        switch prediction {
        case .preloadDatasetContext(let datasetId):
            logger.info("[CrossWorkspace] Preloading dataset context: \(datasetId)")
            // Load themes related to this dataset
            let themes = storageService.loadThemes(sessionId)
            let relevantThemes = themes.filter { $0.entities.contains { $0.contains("data") || $0.contains("dataset") } }
            for theme in relevantThemes.prefix(3) {
                _ = contextPreloader.getCachedTheme(theme.id)  // Warm cache
            }

        case .preloadFileContext(let fileId):
            logger.info("[CrossWorkspace] Preloading file context: \(fileId)")
            _ = contextPreloader.getCachedFile(fileId)

        case .preloadCodeContext(let filePath):
            logger.info("[CrossWorkspace] Preloading code context: \(filePath)")
            let themes = storageService.loadThemes(sessionId)
            let codeThemes = themes.filter { $0.topic.lowercased().contains("code") || $0.content.contains(filePath) }
            for theme in codeThemes.prefix(3) {
                _ = contextPreloader.getCachedTheme(theme.id)
            }

        case .preloadWorkflowContext(let workflowId):
            logger.info("[CrossWorkspace] Preloading workflow context: \(workflowId)")
            // Preload workflow-related themes

        case .preloadKanbanTaskContext(let taskId):
            logger.info("[CrossWorkspace] Preloading kanban task context: \(taskId)")
            // Preload task-related themes

        case .preloadRecentlyMentionedFiles:
            logger.info("[CrossWorkspace] Preloading recently mentioned files")
            let files = storageService.loadFileReferences(sessionId)
            for file in files.sorted(by: { $0.lastAccessed > $1.lastAccessed }).prefix(5) {
                _ = contextPreloader.getCachedFile(file.id)
            }

        case .preloadDiscussedWorkflows:
            logger.info("[CrossWorkspace] Preloading discussed workflows")

        case .preloadRelevantDatasets(let query):
            logger.info("[CrossWorkspace] Preloading relevant datasets for: \(query)")
        }
    }

    // MARK: - Pattern Queries

    /// Get confidence for a specific pattern
    func confidenceFor(pattern: LearnablePattern) -> Float {
        return learnedPatterns[pattern]?.averageConfidence ?? 0.0
    }

    /// Get most common transition patterns
    func commonPatterns(limit: Int = 5) -> [(LearnablePattern, PatternStrength)] {
        return learnedPatterns
            .sorted { $0.value.occurrences > $1.value.occurrences }
            .prefix(limit)
            .map { ($0.key, $0.value) }
    }

    // MARK: - Persistence

    private func savePatterns() {
        // Would persist to storage
        // Simplified for now
    }

    private func loadPatterns() {
        // Would load from storage
    }

    func resetPatterns() {
        learnedPatterns.removeAll()
        transitionHistory.removeAll()
        logger.info("[CrossWorkspace] Reset all patterns")
    }
}

// MARK: - Workspace Transition

struct WorkspaceTransition: Identifiable {
    let id = UUID()
    let from: WorkspaceType
    let to: WorkspaceType
    let context: TransitionContext
    let timestamp: Date
}

// MARK: - Transition Context

struct TransitionContext {
    var activeSessionId: UUID?
    var activeFileId: UUID?
    var activeDatasetId: UUID?
    var activeWorkflowId: UUID?
    var activeKanbanTaskId: UUID?
    var activeCodeFilePath: String?
    var activeTeamId: UUID?
    var activeModelId: String?
    var lastQuery: String?
    var previousWorkspace: WorkspaceType?

    init(
        activeSessionId: UUID? = nil,
        activeFileId: UUID? = nil,
        activeDatasetId: UUID? = nil,
        activeWorkflowId: UUID? = nil,
        activeKanbanTaskId: UUID? = nil,
        activeCodeFilePath: String? = nil,
        activeTeamId: UUID? = nil,
        activeModelId: String? = nil,
        lastQuery: String? = nil,
        previousWorkspace: WorkspaceType? = nil
    ) {
        self.activeSessionId = activeSessionId
        self.activeFileId = activeFileId
        self.activeDatasetId = activeDatasetId
        self.activeWorkflowId = activeWorkflowId
        self.activeKanbanTaskId = activeKanbanTaskId
        self.activeCodeFilePath = activeCodeFilePath
        self.activeTeamId = activeTeamId
        self.activeModelId = activeModelId
        self.lastQuery = lastQuery
        self.previousWorkspace = previousWorkspace
    }
}

// MARK: - Learnable Pattern

enum LearnablePattern: Hashable {
    case dataTabThenChat(datasetId: UUID)
    case vaultFileThenChat(fileId: UUID)
    case workflowThenChat(workflowId: UUID)
    case kanbanThenChat(taskId: UUID)
    case codeFileThenChat(filePath: String)
    case teamChatThenMainChat(teamId: UUID)
    case p2pSyncThenChat
    case huggingFaceDownloadThenChat(modelId: String)
    case genericTransition(from: WorkspaceType, to: WorkspaceType)
}

// MARK: - Pattern Strength

struct PatternStrength {
    var occurrences: Int
    var lastSeen: Date
    var averageConfidence: Float
}

// MARK: - Context Preload Prediction

enum ContextPreloadPrediction {
    case preloadDatasetContext(datasetId: UUID)
    case preloadFileContext(fileId: UUID)
    case preloadCodeContext(filePath: String)
    case preloadWorkflowContext(workflowId: UUID)
    case preloadKanbanTaskContext(taskId: UUID)
    case preloadRecentlyMentionedFiles
    case preloadDiscussedWorkflows
    case preloadRelevantDatasets(query: String)
}

// MARK: - Float Extension

extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        return min(max(self, range.lowerBound), range.upperBound)
    }
}
