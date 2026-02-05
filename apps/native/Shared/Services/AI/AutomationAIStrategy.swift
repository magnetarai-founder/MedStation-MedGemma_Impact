//
//  AutomationAIStrategy.swift
//  MagnetarStudio
//
//  WorkspaceAIStrategy conformer for natural language → automation rule conversion.
//  "Describe what you want automated..." → generates AutomationRule.
//

import Foundation

struct AutomationAIStrategy: WorkspaceAIStrategy {
    var systemPrompt: String {
        """
        You are an automation rule generator. The user will describe what they want automated.
        Generate a JSON automation rule with the following structure:
        {
          "name": "Rule Name",
          "description": "What this rule does",
          "trigger": "onDocumentSave" | "onRecordingStop" | "onSheetCellChange" | "onKanbanStatusChange" | "manual",
          "conditions": [
            {"field": "fieldName", "operator": "equals|contains|greaterThan|lessThan|isEmpty|isNotEmpty", "value": "targetValue"}
          ],
          "actions": [
            {"type": "exportDocument", "format": "PDF"},
            {"type": "runAI", "prompt": "Summarize this document"},
            {"type": "sendNotification", "title": "Alert", "body": "Something happened"},
            {"type": "createNote", "title": "New Note", "content": "Content here"},
            {"type": "moveKanbanTask", "toColumn": "Done"},
            {"type": "updateCell", "address": "A1", "value": "Updated"}
          ]
        }

        Available triggers: onDocumentSave, onRecordingStop, onSheetCellChange, onKanbanStatusChange, manual
        Available condition operators: equals, not equals, contains, not contains, greater than, less than, is empty, is not empty
        Available actions: exportDocument, runAI, sendNotification, createNote, moveKanbanTask, updateCell

        Use {{fieldName}} in action values to reference trigger context fields.
        Available fields depend on trigger:
        - onDocumentSave: documentTitle, content
        - onRecordingStop: recordingTitle, transcript
        - onSheetCellChange: sheetTitle, cellAddress, oldValue, newValue
        - onKanbanStatusChange: taskTitle, fromColumn, toColumn

        Respond ONLY with the JSON object. No explanation text.
        """
    }

    func formatPrompt(action: WorkspaceAIAction, userInput: String, context: String) -> String {
        var prompt = "Create an automation rule for: \(userInput)"
        if !context.isEmpty {
            prompt += "\n\nAdditional context: \(context)"
        }
        return prompt
    }
}
