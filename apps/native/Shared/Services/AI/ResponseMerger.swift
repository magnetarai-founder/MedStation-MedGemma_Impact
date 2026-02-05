//
//  ResponseMerger.swift
//  MagnetarStudio
//
//  Merges and selects responses from multiple model outputs.
//  Used by CodingModelOrchestrator for Parallel mode.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ResponseMerger")

// MARK: - Response Quality Score

/// Quality assessment for a model response
struct ResponseQualityScore: Sendable {
    let score: Float         // 0.0-1.0 overall quality
    let lengthScore: Float   // Appropriate length
    let structureScore: Float  // Well-structured (headers, code blocks, etc.)
    let codeScore: Float     // Code quality (if applicable)
    let relevanceScore: Float  // Relevance to query

    /// Combined weighted score
    var weighted: Float {
        (relevanceScore * 0.35) +
        (structureScore * 0.25) +
        (codeScore * 0.25) +
        (lengthScore * 0.15)
    }
}

// MARK: - Response Merger

/// Service for merging and selecting the best response from multiple model outputs
final class ResponseMerger: @unchecked Sendable {

    // MARK: - Selection

    /// Select the best response from multiple model responses
    func selectBest(
        from responses: [OrchestratedResponse.ModelResponse],
        query: String
    ) -> OrchestratedResponse.ModelResponse {
        guard !responses.isEmpty else {
            logger.error("selectBest called with empty responses — returning empty fallback")
            return OrchestratedResponse.ModelResponse(
                id: UUID(), modelId: "none", modelName: "none",
                role: .primary, content: "", confidence: 0, executionTimeMs: 0
            )
        }

        guard responses.count > 1 else {
            return responses[0]
        }

        // Score each response
        let scored = responses.map { response in
            (response: response, score: scoreResponse(response, query: query))
        }

        // Sort by weighted score
        let sorted = scored.sorted { $0.score.weighted > $1.score.weighted }

        let best = sorted[0]
        logger.debug("[ResponseMerger] Selected \(best.response.modelName) (score: \(best.score.weighted))")

        return OrchestratedResponse.ModelResponse(
            id: best.response.id,
            modelId: best.response.modelId,
            modelName: best.response.modelName,
            role: best.response.role,
            content: best.response.content,
            confidence: best.score.weighted,
            executionTimeMs: best.response.executionTimeMs
        )
    }

    // MARK: - Merging

    /// Merge complementary responses into a single response
    func merge(
        responses: [OrchestratedResponse.ModelResponse],
        query: String
    ) -> String {
        guard !responses.isEmpty else { return "" }
        guard responses.count > 1 else { return responses[0].content }

        // Score and sort
        let scored = responses
            .map { (response: $0, score: scoreResponse($0, query: query)) }
            .sorted { $0.score.weighted > $1.score.weighted }

        // Use best response as base
        var merged = scored[0].response.content

        // Check if other responses have unique code blocks
        for i in 1..<scored.count {
            let otherContent = scored[i].response.content
            let otherCodeBlocks = extractCodeBlocks(from: otherContent)
            let baseCodeBlocks = extractCodeBlocks(from: merged)

            // If other response has code blocks not in base, note them
            let uniqueBlocks = otherCodeBlocks.filter { block in
                !baseCodeBlocks.contains { $0 == block }
            }

            if !uniqueBlocks.isEmpty {
                merged += "\n\n---\n*Alternative from \(scored[i].response.modelName):*\n"
                for block in uniqueBlocks.prefix(2) {
                    merged += "\n```\n\(block)\n```"
                }
            }
        }

        return merged
    }

    // MARK: - Scoring

    private func scoreResponse(
        _ response: OrchestratedResponse.ModelResponse,
        query: String
    ) -> ResponseQualityScore {
        let content = response.content

        let lengthScore = scoreLengthQuality(content, queryLength: query.count)
        let structureScore = scoreStructureQuality(content)
        let codeScore = scoreCodeQuality(content, query: query)
        let relevanceScore = scoreRelevance(content, query: query)

        return ResponseQualityScore(
            score: 0,  // Placeholder, use `weighted`
            lengthScore: lengthScore,
            structureScore: structureScore,
            codeScore: codeScore,
            relevanceScore: relevanceScore
        )
    }

    /// Score based on response length appropriateness
    private func scoreLengthQuality(_ content: String, queryLength: Int) -> Float {
        let length = content.count

        // Very short responses (< 50 chars) likely incomplete
        if length < 50 { return 0.3 }

        // Extremely long responses (> 5000 chars) may be verbose
        if length > 5000 { return 0.7 }

        // Sweet spot: proportional to query complexity
        let idealLength = max(200, queryLength * 3)
        let ratio = Float(length) / Float(idealLength)

        if ratio >= 0.5 && ratio <= 3.0 {
            return 0.9
        } else if ratio > 3.0 {
            return 0.7
        } else {
            return 0.6
        }
    }

    /// Score based on structural quality
    private func scoreStructureQuality(_ content: String) -> Float {
        var score: Float = 0.5

        // Has headers/sections
        if content.contains("##") || content.contains("**") {
            score += 0.1
        }

        // Has code blocks
        if content.contains("```") {
            score += 0.15
        }

        // Has bullet points or numbered lists
        if content.contains("- ") || content.contains("1.") {
            score += 0.1
        }

        // Has paragraphs (multiple line breaks)
        if content.components(separatedBy: "\n\n").count > 1 {
            score += 0.1
        }

        // Penalize raw unformatted dumps
        if !content.contains("\n") && content.count > 200 {
            score -= 0.2
        }

        return min(1.0, max(0.0, score))
    }

    /// Score based on code quality (if code-related query)
    private func scoreCodeQuality(_ content: String, query: String) -> Float {
        let queryLower = query.lowercased()
        let isCodeQuery = queryLower.contains("code") || queryLower.contains("implement") ||
                          queryLower.contains("function") || queryLower.contains("write")

        if !isCodeQuery {
            return 0.5  // Neutral for non-code queries
        }

        let codeBlocks = extractCodeBlocks(from: content)

        if codeBlocks.isEmpty {
            return 0.3  // Code query but no code blocks
        }

        var score: Float = 0.7

        // Check code blocks for quality indicators
        for block in codeBlocks {
            // Has function/class definitions
            if block.contains("func ") || block.contains("function") ||
               block.contains("def ") || block.contains("class ") {
                score += 0.1
            }

            // Has comments
            if block.contains("//") || block.contains("#") || block.contains("/*") {
                score += 0.05
            }

            // Reasonable length
            if block.count > 20 && block.count < 2000 {
                score += 0.05
            }
        }

        return min(1.0, score)
    }

    /// Score based on relevance to query
    private func scoreRelevance(_ content: String, query: String) -> Float {
        let queryWords = query.lowercased().split(separator: " ")
            .filter { $0.count > 3 }  // Skip short words
            .map { String($0) }

        let contentLower = content.lowercased()

        // Count how many query keywords appear in response
        let matchCount = queryWords.filter { contentLower.contains($0) }.count
        let matchRatio = Float(matchCount) / Float(max(1, queryWords.count))

        return min(1.0, matchRatio + 0.3)  // Base score of 0.3
    }

    // MARK: - Helpers

    /// Extract code blocks from markdown content
    private func extractCodeBlocks(from content: String) -> [String] {
        let pattern = "```(?:\\w+)?\\n([\\s\\S]*?)```"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            return []
        }

        let range = NSRange(content.startIndex..., in: content)
        let matches = regex.matches(in: content, options: [], range: range)

        return matches.compactMap { match in
            guard match.numberOfRanges > 1,
                  let codeRange = Range(match.range(at: 1), in: content) else {
                return nil
            }
            return String(content[codeRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }
}
