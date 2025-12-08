//
//  WorkflowQueueModels.swift
//  MagnetarStudio
//
//  Data models for workflow queue
//

import SwiftUI

// MARK: - Models

enum QueueViewMode {
    case available
    case myActive
}

enum PriorityFilter: String {
    case all = "All Priorities"
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var displayName: String {
        rawValue
    }

    func toPriority() -> ItemPriority? {
        switch self {
        case .all: return nil
        case .high: return .high
        case .medium: return .medium
        case .low: return .low
        }
    }
}

enum ItemPriority: String {
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var emoji: String {
        switch self {
        case .high: return "🔴"
        case .medium: return "🟡"
        case .low: return "🟢"
        }
    }
}

struct QueueItem: Identifiable {
    let id = UUID()
    let reference: String
    let workflowName: String
    let stageName: String
    let priority: ItemPriority
    let statusLabels: [String]
    let dataPreview: [(key: String, value: String)]
    let createdAt: String
    let tags: [String]
    let assignedTo: String?
    let isAssignedToMe: Bool

    static let mockItems = [
        QueueItem(
            reference: "WRK-1234",
            workflowName: "Customer Onboarding",
            stageName: "Identity Verification",
            priority: .high,
            statusLabels: ["Pending", "Review"],
            dataPreview: [
                (key: "Customer ID", value: "CUST-5678"),
                (key: "Email", value: "alice@example.com"),
                (key: "Status", value: "Documents Uploaded")
            ],
            createdAt: "2h ago",
            tags: ["onboarding", "urgent"],
            assignedTo: "Alice Johnson",
            isAssignedToMe: true
        ),
        QueueItem(
            reference: "WRK-1235",
            workflowName: "Data Processing Pipeline",
            stageName: "Validation",
            priority: .medium,
            statusLabels: ["In Progress"],
            dataPreview: [
                (key: "Batch ID", value: "BATCH-9012"),
                (key: "Records", value: "1,245"),
                (key: "Progress", value: "67%")
            ],
            createdAt: "5h ago",
            tags: ["data", "pipeline"],
            assignedTo: "Bob Smith",
            isAssignedToMe: false
        ),
        QueueItem(
            reference: "WRK-1236",
            workflowName: "Support Ticket Resolution",
            stageName: "Initial Triage",
            priority: .low,
            statusLabels: ["Pending"],
            dataPreview: [
                (key: "Ticket ID", value: "TKT-3456"),
                (key: "Subject", value: "Login Issue"),
                (key: "Customer", value: "Carol Davis")
            ],
            createdAt: "1d ago",
            tags: ["support"],
            assignedTo: nil,
            isAssignedToMe: false
        ),
        QueueItem(
            reference: "WRK-1237",
            workflowName: "Invoice Approval",
            stageName: "Finance Review",
            priority: .high,
            statusLabels: ["Review", "Blocked"],
            dataPreview: [
                (key: "Invoice", value: "INV-7890"),
                (key: "Amount", value: "$12,450.00"),
                (key: "Vendor", value: "Acme Corp")
            ],
            createdAt: "30m ago",
            tags: ["finance", "urgent"],
            assignedTo: "David Wilson",
            isAssignedToMe: true
        ),
        QueueItem(
            reference: "WRK-1238",
            workflowName: "Content Publication",
            stageName: "Editorial Review",
            priority: .medium,
            statusLabels: ["In Progress"],
            dataPreview: [
                (key: "Article ID", value: "ART-1122"),
                (key: "Title", value: "Q4 Product Roadmap"),
                (key: "Author", value: "Eve Martinez")
            ],
            createdAt: "3h ago",
            tags: ["content", "marketing"],
            assignedTo: "Eve Martinez",
            isAssignedToMe: false
        )
    ]
}

// MARK: - Preview

#Preview {
    WorkflowQueueView()
        .frame(width: 1200, height: 800)
}
