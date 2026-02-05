//
//  TemplateAIStrategy.swift
//  MagnetarStudio
//
//  AI strategy for generating templates from natural language descriptions.
//  Extends WorkspaceAIStrategy to create template block structures via AI.
//

import Foundation

struct TemplateAIStrategy: WorkspaceAIStrategy {
    var systemPrompt: String {
        """
        You are a template designer for a document editor. Given a description of what the user wants, \
        generate a structured template using these block types: text, heading1, heading2, heading3, \
        bulletList, numberedList, checkbox, code, quote, divider, calloutInfo, calloutWarning, \
        calloutSuccess, calloutError.

        Output ONLY a JSON array of blocks, each with "type" and "content" fields.
        Use {{variableName}} placeholders for parts the user should fill in.

        Example output:
        [
          {"type": "heading1", "content": "{{title}}"},
          {"type": "text", "content": "Created by {{author}} on {{date}}"},
          {"type": "heading2", "content": "Overview"},
          {"type": "text", "content": ""}
        ]
        """
    }

    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String {
        "Create a template for: \(userInput)"
    }

    func parseResponse(_ response: String) -> String {
        // Extract JSON array from response (may be wrapped in markdown code block)
        var cleaned = response
        if let start = cleaned.range(of: "["), let end = cleaned.range(of: "]", options: .backwards) {
            cleaned = String(cleaned[start.lowerBound...end.upperBound])
        }
        return cleaned
    }
}
