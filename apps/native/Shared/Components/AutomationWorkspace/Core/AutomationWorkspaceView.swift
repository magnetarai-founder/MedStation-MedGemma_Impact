//
//  AutomationWorkspaceView.swift
//  MagnetarStudio
//
//  Main automation workspace orchestrator view
//

import SwiftUI

struct AutomationWorkspaceView: View {
    @State private var selectedView: WorkflowView = .queue
    @State private var searchText: String = ""

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.05))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content
            contentArea
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // View tabs
            HStack(spacing: 4) {
                ForEach(WorkflowView.allCases, id: \.self) { view in
                    WorkflowTabButton(
                        title: view.displayName,
                        icon: view.icon,
                        isActive: selectedView == view,
                        action: { selectedView = view }
                    )
                }
            }

            Spacer()

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)

                TextField("Search workflows...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color.gray.opacity(0.1))
            )
            .frame(width: 240)

            // New workflow button
            Button {
                // Create new workflow
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "plus")
                        .font(.system(size: 16))
                    Text("New Workflow")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        switch selectedView {
        case .queue:
            WorkflowQueueView()
        case .dashboard:
            WorkflowDashboardView()
        case .builder:
            WorkflowBuilderView()
        case .designer:
            WorkflowDesignerView()
        case .analytics:
            WorkflowAnalyticsView()
        }
    }
}

// MARK: - Supporting Types

enum WorkflowView: String, CaseIterable {
    case queue
    case dashboard
    case builder
    case designer
    case analytics

    var displayName: String {
        switch self {
        case .queue: return "Queue"
        case .dashboard: return "Dashboard"
        case .builder: return "Builder"
        case .designer: return "Designer"
        case .analytics: return "Analytics"
        }
    }

    var icon: String {
        switch self {
        case .queue: return "list.bullet.clipboard"
        case .dashboard: return "chart.bar"
        case .builder: return "square.and.pencil"
        case .designer: return "paintbrush"
        case .analytics: return "chart.line.uptrend.xyaxis"
        }
    }
}

// MARK: - Preview

#Preview {
    AutomationWorkspaceView()
        .frame(width: 1200, height: 800)
}
