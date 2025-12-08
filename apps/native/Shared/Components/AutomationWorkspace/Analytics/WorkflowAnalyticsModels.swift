//
//  WorkflowAnalyticsModels.swift
//  MagnetarStudio
//
//  Data models for workflow analytics
//

import SwiftUI

// MARK: - Analytics Models

// Legacy mock analytics model used for the UI preview; renamed to avoid clashing with backend model.
struct LegacyWorkflowAnalytics {
    let totalItems: Int
    let completedItems: Int
    let inProgressItems: Int
    let cancelledItems: Int
    let failedItems: Int
    let avgCycleTime: String
    let medianCycleTime: String?
    let stagePerformance: [LegacyStagePerformance]

    var completionPercent: Int {
        guard totalItems > 0 else { return 0 }
        return Int((Double(completedItems) / Double(totalItems)) * 100)
    }

    static let mock = LegacyWorkflowAnalytics(
        totalItems: 1847,
        completedItems: 1523,
        inProgressItems: 287,
        cancelledItems: 24,
        failedItems: 13,
        avgCycleTime: "3.2h",
        medianCycleTime: "2.8h",
        stagePerformance: [
            LegacyStagePerformance(name: "Initial Triage", entered: 1847, completed: 1823, avgTime: "12m", medianTime: "10m"),
            LegacyStagePerformance(name: "Data Validation", entered: 1823, completed: 1789, avgTime: "45m", medianTime: "38m"),
            LegacyStagePerformance(name: "Processing", entered: 1789, completed: 1654, avgTime: "1.8h", medianTime: "1.5h"),
            LegacyStagePerformance(name: "Review", entered: 1654, completed: 1598, avgTime: "2.3h", medianTime: "2.0h"),
            LegacyStagePerformance(name: "Approval", entered: 1598, completed: 1523, avgTime: "4.1h", medianTime: "3.2h")
        ]
    )
}

struct LegacyStagePerformance: Identifiable {
    let id = UUID()
    let name: String
    let entered: Int
    let completed: Int
    let avgTime: String
    let medianTime: String?
}
