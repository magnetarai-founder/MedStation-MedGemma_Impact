//
//  WorkspaceAIStrategy.swift
//  MagnetarStudio
//
//  Per-panel AI strategy protocol and concrete implementations.
//  Each strategy defines the system prompt and prompt formatting for its domain.
//

import Foundation

// MARK: - Protocol

/// Strategy defining how AI interacts with a specific workspace panel.
protocol WorkspaceAIStrategy: Sendable {
    /// System prompt establishing the AI's role
    var systemPrompt: String { get }

    /// Format the user's input into a model-ready prompt
    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String

    /// Parse model response (default: return as-is)
    func parseResponse(_ response: String) -> String
}

extension WorkspaceAIStrategy {
    func parseResponse(_ response: String) -> String { response }
}

// MARK: - Text Strategy (Notes + Docs)

/// AI strategy for writing assistance in Notes and Docs panels.
struct TextAIStrategy: WorkspaceAIStrategy {
    var systemPrompt: String {
        """
        You are a writing assistant integrated into a note-taking and document editing app. \
        Your responses should be clean text ready to insert directly into the document. \
        Do not wrap your response in quotes or add preamble like "Here's the improved version:". \
        Just output the improved text directly.
        """
    }

    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String {
        let contextSection = context.isEmpty ? "" : "\nDocument context:\n\(context)\n"

        switch action {
        case .improveWriting:
            return """
            Rewrite the following text for better clarity, flow, and readability. \
            Preserve the original meaning and tone.\(contextSection)
            Text to improve:
            \(userInput)
            """

        case .makeShorter:
            return """
            Condense the following text to roughly half its length. \
            Keep all key points and maintain the same tone.\(contextSection)
            Text to shorten:
            \(userInput)
            """

        case .makeLonger:
            return """
            Expand the following text with additional detail, examples, or explanation. \
            Maintain the same style and tone.\(contextSection)
            Text to expand:
            \(userInput)
            """

        case .fixGrammar:
            return """
            Fix only grammar, spelling, and punctuation errors in the following text. \
            Do not change the style, tone, or meaning.\(contextSection)
            Text to fix:
            \(userInput)
            """

        case .toneProfessional:
            return """
            Rewrite the following text in a formal, professional business tone. \
            Keep the same information.\(contextSection)
            Text to rewrite:
            \(userInput)
            """

        case .toneCasual:
            return """
            Rewrite the following text in a friendly, conversational tone. \
            Keep the same information.\(contextSection)
            Text to rewrite:
            \(userInput)
            """

        case .summarize:
            return """
            Create a concise 2-3 sentence summary of the following text.\(contextSection)
            Text to summarize:
            \(userInput)
            """

        case .askAI:
            return """
            \(contextSection)
            \(userInput)
            """

        default:
            return userInput
        }
    }
}

// MARK: - Sheets Strategy

/// AI strategy for spreadsheet formula generation and explanation.
struct SheetsAIStrategy: WorkspaceAIStrategy {
    var systemPrompt: String {
        """
        You are a spreadsheet formula assistant. You help users create formulas and explain existing ones.

        Available functions: SUM, AVERAGE, COUNT, MIN, MAX, IF, CONCATENATE, SUMIF, \
        COUNTIF, VLOOKUP, INDEX, MATCH, LEFT, RIGHT, MID, LEN, TRIM, UPPER, LOWER, ROUND.

        Cell references use the format: A1, B2, $A$1 (absolute), A1:B10 (ranges).
        Formulas start with =.

        When generating a formula, output ONLY the formula on the first line, \
        then a blank line, then a brief explanation.
        """
    }

    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String {
        let contextSection = context.isEmpty ? "" : "\nSpreadsheet context:\n\(context)\n"

        switch action {
        case .generateFormula:
            return """
            Generate a spreadsheet formula for the following request.\(contextSection)
            Request: \(userInput)
            """

        case .explainFormula:
            return """
            Explain what this spreadsheet formula does in plain English.\(contextSection)
            Formula: \(userInput)
            """

        default:
            return userInput
        }
    }

    /// Extract just the formula from the response (first line starting with =)
    func parseFormula(_ response: String) -> String? {
        let lines = response.components(separatedBy: .newlines)
        return lines.first { $0.trimmingCharacters(in: .whitespaces).hasPrefix("=") }?
            .trimmingCharacters(in: .whitespaces)
    }

    /// Extract the explanation (everything after the formula line)
    func parseExplanation(_ response: String) -> String {
        let lines = response.components(separatedBy: .newlines)
        let afterFormula = lines.drop { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("=") }
            .dropFirst()
            .joined(separator: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return afterFormula.isEmpty ? response : afterFormula
    }
}

// MARK: - Voice Strategy

/// AI strategy for voice transcription cleanup and summarization.
struct VoiceAIStrategy: WorkspaceAIStrategy {
    var systemPrompt: String {
        """
        You are a transcription assistant. You clean up speech-to-text transcriptions \
        and create summaries of recorded audio content. \
        Output clean text directly without preamble.
        """
    }

    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String {
        switch action {
        case .cleanTranscription:
            return """
            Clean up this speech-to-text transcription. Fix punctuation, remove filler words \
            (um, uh, like, you know), fix obvious misheard words, and format into proper paragraphs. \
            Keep the original meaning intact.

            Raw transcription:
            \(userInput)
            """

        case .summarizeRecording:
            return """
            Summarize the key points from this voice recording transcription in 3-5 bullet points.

            Transcription:
            \(userInput)
            """

        default:
            return userInput
        }
    }
}
