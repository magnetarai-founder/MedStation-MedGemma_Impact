//
//  WorkflowDashboardModels.swift
//  MagnetarStudio
//
//  Dashboard models for workflow management - Extracted from AutomationWorkspace.swift
//

import SwiftUI

// MARK: - Dashboard Models

enum DashboardScope: String {
    case all = "All Workflows"
    case my = "My Workflows"
    case team = "Team Workflows"

    var displayName: String { rawValue }
}

enum WorkflowVisibility {
    case `private`
    case team
    case `public`

    var icon: String {
        switch self {
        case .private: return "lock.fill"
        case .team: return "person.2.fill"
        case .public: return "globe"
        }
    }

    var displayName: String {
        switch self {
        case .private: return "Private"
        case .team: return "Team"
        case .public: return "Public"
        }
    }
}

struct WorkflowCard: Identifiable {
    let id = UUID()
    let name: String
    let description: String
    let icon: String
    let typeName: String
    let typeColor: Color
    let isTemplate: Bool
    let visibility: WorkflowVisibility

    static let mockStarred = [
        WorkflowCard(
            name: "Customer Onboarding",
            description: "Automated workflow for onboarding new customers with identity verification and account setup",
            icon: "person.badge.plus",
            typeName: "Onboarding",
            typeColor: .green,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Invoice Processing",
            description: "Extract data from invoices, validate amounts, and route for approval",
            icon: "doc.text",
            typeName: "Finance",
            typeColor: .blue,
            isTemplate: false,
            visibility: .private
        ),
        WorkflowCard(
            name: "Support Ticket Triage",
            description: "Classify incoming support tickets and assign to appropriate teams",
            icon: "ticket",
            typeName: "Support",
            typeColor: .orange,
            isTemplate: true,
            visibility: .public
        )
    ]

    static let mockRecent = [
        WorkflowCard(
            name: "Data Pipeline ETL",
            description: "Extract, transform, and load data from multiple sources into data warehouse",
            icon: "arrow.triangle.branch",
            typeName: "Data",
            typeColor: .purple,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Content Publication",
            description: "Review, approve, and publish content across multiple channels",
            icon: "doc.richtext",
            typeName: "Content",
            typeColor: .pink,
            isTemplate: false,
            visibility: .team
        ),
        WorkflowCard(
            name: "Security Incident Response",
            description: "Automated playbook for security incident detection, analysis, and remediation",
            icon: "shield",
            typeName: "Security",
            typeColor: .red,
            isTemplate: true,
            visibility: .public
        ),
        WorkflowCard(
            name: "Code Review Automation",
            description: "Automated code quality checks, test execution, and PR review routing",
            icon: "chevron.left.forwardslash.chevron.right",
            typeName: "DevOps",
            typeColor: .cyan,
            isTemplate: false,
            visibility: .team
        )
    ]
}
