//
//  SmartFilePicker.swift
//  MagnetarStudio
//
//  ANE-powered smart file picker that suggests relevant files.
//  Integrates with cross-conversation index for intelligent suggestions.
//

import Foundation
import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "SmartFilePicker")

// MARK: - Smart File Picker Service

@MainActor
final class SmartFilePickerService: ObservableObject {

    // MARK: - Published State

    @Published private(set) var suggestions: [FileSuggestion] = []
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var lastQuery: String?

    // MARK: - Dependencies

    private let fileIndex: CrossConversationFileIndex
    private let relevanceScorer: FileRelevanceScorer
    private let predictor: ANEPredictor
    private let embedder: HashEmbedder

    // MARK: - Configuration

    var configuration: SmartPickerConfiguration = .default

    // MARK: - Singleton

    static let shared = SmartFilePickerService()

    // MARK: - Initialization

    init(
        fileIndex: CrossConversationFileIndex? = nil,
        relevanceScorer: FileRelevanceScorer? = nil,
        predictor: ANEPredictor? = nil,
        embedder: HashEmbedder? = nil
    ) {
        self.fileIndex = fileIndex ?? .shared
        self.relevanceScorer = relevanceScorer ?? .shared
        self.predictor = predictor ?? .shared
        self.embedder = embedder ?? .shared
    }

    // MARK: - Suggestion Generation

    /// Generate file suggestions based on current context
    func generateSuggestions(
        for context: PickerContext,
        availableFiles: [FileReference]
    ) async {
        isLoading = true
        defer { isLoading = false }

        lastQuery = context.query

        var allSuggestions: [FileSuggestion] = []

        // 1. Score available files by relevance
        if let query = context.query, !query.isEmpty {
            let scoringContext = ScoringContext(
                currentWorkspace: context.workspace,
                currentConversationId: context.conversationId,
                activeFileIds: context.activeFileIds,
                recentQuery: query,
                preferredFileTypes: context.preferredFileTypes,
                keywords: extractKeywords(from: query)
            )

            let scores = await relevanceScorer.topRelevantFiles(
                from: availableFiles,
                query: query,
                context: scoringContext,
                count: configuration.maxSuggestions
            )

            for score in scores {
                if let file = availableFiles.first(where: { $0.id == score.fileId }) {
                    allSuggestions.append(FileSuggestion(
                        file: file,
                        score: score.totalScore,
                        reason: .relevantToQuery,
                        explanation: score.explanation
                    ))
                }
            }
        }

        // 2. Add ANE-predicted files
        let predicted = await getANEPredictedFiles(context: context, availableFiles: availableFiles)
        for prediction in predicted where !allSuggestions.contains(where: { $0.file.id == prediction.file.id }) {
            allSuggestions.append(prediction)
        }

        // 3. Add cross-conversation files
        if configuration.includeCrossConversation {
            let crossConv = await getCrossConversationSuggestions(context: context)
            for suggestion in crossConv where !allSuggestions.contains(where: { $0.file.id == suggestion.file.id }) {
                allSuggestions.append(suggestion)
            }
        }

        // 4. Add recently accessed files
        let recent = getRecentlyAccessedSuggestions(from: availableFiles, limit: 3)
        for suggestion in recent where !allSuggestions.contains(where: { $0.file.id == suggestion.file.id }) {
            allSuggestions.append(suggestion)
        }

        // 5. Sort by score and limit
        allSuggestions.sort { $0.score > $1.score }
        suggestions = Array(allSuggestions.prefix(configuration.maxSuggestions))

        logger.debug("[SmartPicker] Generated \(self.suggestions.count) suggestions")
    }

    /// Get suggestions for typing-ahead (as user types query)
    func getSuggestionsForTypeahead(
        partialQuery: String,
        availableFiles: [FileReference],
        limit: Int = 5
    ) async -> [FileSuggestion] {
        guard partialQuery.count >= 2 else { return [] }

        // Quick semantic search
        let queryEmbedding = embedder.embed(partialQuery)
        var scored: [(FileReference, Float)] = []

        for file in availableFiles {
            let fileEmbedding: [Float]
            if let existing = file.embedding {
                fileEmbedding = existing
            } else {
                fileEmbedding = embedder.embed(file.processedContent ?? file.filename)
            }

            let similarity = HashEmbedder.cosineSimilarity(queryEmbedding, fileEmbedding)
            if similarity > 0.25 {
                scored.append((file, similarity))
            }
        }

        scored.sort { $0.1 > $1.1 }

        return scored.prefix(limit).map { file, similarity in
            FileSuggestion(
                file: file,
                score: similarity,
                reason: .relevantToQuery,
                explanation: "Matches your search"
            )
        }
    }

    /// Get co-accessed file suggestions based on active file
    func getCoAccessedSuggestions(activeFileId: UUID, limit: Int = 5) async -> [FileSuggestion] {
        let coAccessed = await fileIndex.getCoAccessedFiles(with: activeFileId, limit: limit)

        return coAccessed.map { result in
            FileSuggestion(
                file: FileReference(
                    id: result.fileId,
                    filename: result.filename,
                    fileType: result.fileType,
                    isVaultProtected: result.isVaultProtected
                ),
                score: result.combinedScore,
                reason: .frequentlyUsedTogether,
                explanation: "Often used with your current file"
            )
        }
    }

    // MARK: - Private Methods

    private func getANEPredictedFiles(
        context: PickerContext,
        availableFiles: [FileReference]
    ) async -> [FileSuggestion] {
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: context.workspace,
            recentQuery: context.query,
            activeFileId: context.activeFileIds.first
        )

        var suggestions: [FileSuggestion] = []

        // Find files matching predicted topics
        for topic in prediction.likelyTopics.prefix(3) {
            for file in availableFiles {
                let fileText = (file.processedContent ?? file.filename).lowercased()
                if fileText.contains(topic.lowercased()) {
                    suggestions.append(FileSuggestion(
                        file: file,
                        score: 0.6,  // ANE predictions get moderate score
                        reason: .anePredicted,
                        explanation: "Predicted based on your patterns (\(topic))"
                    ))
                    break  // One file per topic
                }
            }
        }

        return suggestions
    }

    private func getCrossConversationSuggestions(context: PickerContext) async -> [FileSuggestion] {
        guard let query = context.query, !query.isEmpty else { return [] }

        let results = await fileIndex.findRelevantFiles(
            query: query,
            limit: 5,
            excludeConversation: context.conversationId,
            minSimilarity: 0.35
        )

        return results.map { result in
            FileSuggestion(
                file: FileReference(
                    id: result.fileId,
                    filename: result.filename,
                    fileType: result.fileType,
                    isVaultProtected: result.isVaultProtected
                ),
                score: result.combinedScore * 0.9,  // Slight penalty for cross-conversation
                reason: .fromRelatedConversation,
                explanation: "Used in \(result.conversationCount) other conversation\(result.conversationCount > 1 ? "s" : "")"
            )
        }
    }

    private func getRecentlyAccessedSuggestions(from files: [FileReference], limit: Int) -> [FileSuggestion] {
        let sorted = files.sorted { $0.lastAccessed > $1.lastAccessed }

        return sorted.prefix(limit).map { file in
            let recencyScore = calculateRecencyScore(file.lastAccessed)
            return FileSuggestion(
                file: file,
                score: recencyScore * 0.8,  // Recent files get moderate-high score
                reason: .recentlyAccessed,
                explanation: "Accessed \(formatTimeAgo(file.lastAccessed))"
            )
        }
    }

    private func extractKeywords(from query: String) -> [String] {
        let words = query.components(separatedBy: .whitespacesAndNewlines)
            .filter { $0.count >= 3 }
            .map { $0.lowercased() }

        // Filter out common words
        let stopWords: Set<String> = ["the", "and", "for", "with", "this", "that", "from", "have", "are"]
        return words.filter { !stopWords.contains($0) }
    }

    private func calculateRecencyScore(_ lastAccessed: Date) -> Float {
        let hoursSince = Date().timeIntervalSince(lastAccessed) / 3600
        return Float(max(0, 1 - (hoursSince / 168)))  // Decay over 1 week
    }

    private func formatTimeAgo(_ date: Date) -> String {
        let seconds = Date().timeIntervalSince(date)

        if seconds < 60 {
            return "just now"
        } else if seconds < 3600 {
            let minutes = Int(seconds / 60)
            return "\(minutes) minute\(minutes == 1 ? "" : "s") ago"
        } else if seconds < 86400 {
            let hours = Int(seconds / 3600)
            return "\(hours) hour\(hours == 1 ? "" : "s") ago"
        } else {
            let days = Int(seconds / 86400)
            return "\(days) day\(days == 1 ? "" : "s") ago"
        }
    }
}

// MARK: - Supporting Types

/// Context for the file picker
struct PickerContext {
    var workspace: WorkspaceType = .chat
    var conversationId: UUID?
    var query: String?
    var activeFileIds: [UUID] = []
    var preferredFileTypes: [String] = []

    static func forChat(conversationId: UUID?, query: String?) -> PickerContext {
        return PickerContext(
            workspace: .chat,
            conversationId: conversationId,
            query: query
        )
    }

    static func forCode(activeFiles: [UUID], query: String?) -> PickerContext {
        return PickerContext(
            workspace: .code,
            query: query,
            activeFileIds: activeFiles,
            preferredFileTypes: ["swift", "python", "js", "ts"]
        )
    }
}

/// A file suggestion with explanation
struct FileSuggestion: Identifiable {
    var id: UUID { file.id }

    let file: FileReference
    let score: Float
    let reason: SuggestionReason
    let explanation: String

    /// Icon for the suggestion reason
    var reasonIcon: String {
        switch reason {
        case .relevantToQuery: return "magnifyingglass"
        case .anePredicted: return "brain.head.profile"
        case .fromRelatedConversation: return "bubble.left.and.bubble.right"
        case .frequentlyUsedTogether: return "link"
        case .recentlyAccessed: return "clock"
        case .matchesFileType: return "doc"
        }
    }

    /// Short reason text for UI
    var shortReason: String {
        switch reason {
        case .relevantToQuery: return "Relevant"
        case .anePredicted: return "Suggested"
        case .fromRelatedConversation: return "Related"
        case .frequentlyUsedTogether: return "Co-used"
        case .recentlyAccessed: return "Recent"
        case .matchesFileType: return "Type match"
        }
    }
}

/// Reason for suggesting a file
enum SuggestionReason: String, CaseIterable {
    case relevantToQuery
    case anePredicted
    case fromRelatedConversation
    case frequentlyUsedTogether
    case recentlyAccessed
    case matchesFileType
}

/// Configuration for smart picker behavior
struct SmartPickerConfiguration {
    var maxSuggestions: Int = 10
    var includeCrossConversation: Bool = true
    var includeANEPredictions: Bool = true
    var minRelevanceScore: Float = 0.2
    var typeaheadDelay: TimeInterval = 0.3

    static let `default` = SmartPickerConfiguration()

    static let minimal = SmartPickerConfiguration(
        maxSuggestions: 5,
        includeCrossConversation: false,
        includeANEPredictions: false
    )

    static let comprehensive = SmartPickerConfiguration(
        maxSuggestions: 15,
        includeCrossConversation: true,
        includeANEPredictions: true,
        minRelevanceScore: 0.15
    )
}

// MARK: - Smart File Picker View

struct SmartFilePicker: View {
    @StateObject private var pickerService = SmartFilePickerService.shared

    @Binding var selectedFiles: [FileReference]
    let availableFiles: [FileReference]
    let context: PickerContext
    let onSelect: ((FileReference) -> Void)?

    @State private var searchQuery: String = ""
    @State private var showAllFiles: Bool = false

    init(
        selectedFiles: Binding<[FileReference]>,
        availableFiles: [FileReference],
        context: PickerContext,
        onSelect: ((FileReference) -> Void)? = nil
    ) {
        self._selectedFiles = selectedFiles
        self.availableFiles = availableFiles
        self.context = context
        self.onSelect = onSelect
    }

    var body: some View {
        VStack(spacing: 0) {
            // Search bar
            searchBar

            Divider()

            // Suggestions or all files
            if showAllFiles {
                allFilesList
            } else {
                suggestionsList
            }
        }
        .task {
            await pickerService.generateSuggestions(
                for: context,
                availableFiles: availableFiles
            )
        }
        .onChange(of: searchQuery) { _, newValue in
            Task {
                let updatedContext = PickerContext(
                    workspace: context.workspace,
                    conversationId: context.conversationId,
                    query: newValue.isEmpty ? context.query : newValue,
                    activeFileIds: context.activeFileIds,
                    preferredFileTypes: context.preferredFileTypes
                )
                await pickerService.generateSuggestions(
                    for: updatedContext,
                    availableFiles: availableFiles
                )
            }
        }
    }

    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)

            TextField("Search files...", text: $searchQuery)
                .textFieldStyle(.plain)

            if !searchQuery.isEmpty {
                Button {
                    searchQuery = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            Toggle(isOn: $showAllFiles) {
                Text("All")
                    .font(.caption)
            }
            .toggleStyle(.button)
            .buttonStyle(.bordered)
            .controlSize(.small)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var suggestionsList: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                if pickerService.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding()
                } else if pickerService.suggestions.isEmpty {
                    emptyState
                } else {
                    ForEach(pickerService.suggestions) { suggestion in
                        SuggestionRow(
                            suggestion: suggestion,
                            isSelected: selectedFiles.contains { $0.id == suggestion.file.id },
                            onTap: {
                                toggleSelection(suggestion.file)
                            }
                        )
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
    }

    private var allFilesList: some View {
        ScrollView {
            LazyVStack(spacing: 4) {
                ForEach(filteredFiles) { file in
                    FileRow(
                        file: file,
                        isSelected: selectedFiles.contains { $0.id == file.id },
                        onTap: {
                            toggleSelection(file)
                        }
                    )
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "doc.questionmark")
                .font(.largeTitle)
                .foregroundStyle(.secondary)

            Text("No suggestions available")
                .font(.headline)

            Text("Try searching or browse all files")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }

    private var filteredFiles: [FileReference] {
        if searchQuery.isEmpty {
            return availableFiles.sorted { $0.lastAccessed > $1.lastAccessed }
        }

        let query = searchQuery.lowercased()
        return availableFiles.filter {
            $0.filename.lowercased().contains(query) ||
            ($0.processedContent?.lowercased().contains(query) ?? false)
        }
    }

    private func toggleSelection(_ file: FileReference) {
        if let index = selectedFiles.firstIndex(where: { $0.id == file.id }) {
            selectedFiles.remove(at: index)
        } else {
            selectedFiles.append(file)
            onSelect?(file)
        }
    }
}

// MARK: - Helper Views

private struct SuggestionRow: View {
    let suggestion: FileSuggestion
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                // Selection indicator
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? Color.accentColor : .secondary)

                // File icon
                FileTypeIcon(fileType: suggestion.file.fileType)

                VStack(alignment: .leading, spacing: 2) {
                    Text(suggestion.file.filename)
                        .font(.body)
                        .lineLimit(1)

                    HStack(spacing: 4) {
                        Image(systemName: suggestion.reasonIcon)
                            .font(.caption2)

                        Text(suggestion.explanation)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }

                Spacer()

                // Score indicator
                ScoreBadge(score: suggestion.score)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(isSelected ? Color.accentColor.opacity(0.1) : Color.clear)
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }
}

private struct FileRow: View {
    let file: FileReference
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? Color.accentColor : .secondary)

                FileTypeIcon(fileType: file.fileType)

                Text(file.filename)
                    .font(.body)
                    .lineLimit(1)

                Spacer()

                if file.isVaultProtected {
                    Image(systemName: "lock.shield.fill")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
            .padding(.vertical, 6)
            .padding(.horizontal, 8)
            .background(isSelected ? Color.accentColor.opacity(0.1) : Color.clear)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
    }
}

private struct FileTypeIcon: View {
    let fileType: String

    var body: some View {
        Image(systemName: iconName)
            .font(.title3)
            .foregroundStyle(iconColor)
            .frame(width: 24)
    }

    private var iconName: String {
        let type = fileType.lowercased()

        if type.contains("swift") || type.contains("code") {
            return "swift"
        } else if type.contains("python") {
            return "chevron.left.forwardslash.chevron.right"
        } else if type.contains("javascript") || type.contains("typescript") {
            return "curlybraces"
        } else if type.contains("image") || type.contains("png") || type.contains("jpg") {
            return "photo"
        } else if type.contains("pdf") {
            return "doc.richtext"
        } else if type.contains("markdown") || type.contains("md") {
            return "text.justify.left"
        } else {
            return "doc.text"
        }
    }

    private var iconColor: Color {
        let type = fileType.lowercased()

        if type.contains("swift") {
            return .orange
        } else if type.contains("python") {
            return .blue
        } else if type.contains("javascript") {
            return .yellow
        } else if type.contains("typescript") {
            return .blue
        } else {
            return .gray
        }
    }
}

private struct ScoreBadge: View {
    let score: Float

    var body: some View {
        Text("\(Int(score * 100))%")
            .font(.caption2)
            .fontWeight(.medium)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(backgroundColor)
            .foregroundStyle(.white)
            .cornerRadius(4)
    }

    private var backgroundColor: Color {
        switch score {
        case 0.8...: return .green
        case 0.5..<0.8: return .orange
        default: return .gray
        }
    }
}
