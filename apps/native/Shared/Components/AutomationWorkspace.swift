//
//  AutomationWorkspace.swift
//  MagnetarStudio
//
//  Workflows and automation workspace matching React specs
//  - Tabbed layout: Queue, Dashboard, Builder, Designer, Analytics
//  - Each view has specific toolbar and content matching React files
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
                    .foregroundColor(.secondary)

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
                .foregroundColor(.white)
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

// MARK: - Workflow Tab Button

struct WorkflowTabButton: View {
    let title: String
    let icon: String
    let isActive: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                Text(title)
                    .font(.system(size: 14, weight: isActive ? .medium : .regular))
            }
            .foregroundColor(isActive ? Color.magnetarPrimary : (isHovered ? .primary : .secondary))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Workflow Views (Placeholders with proper structure)

struct WorkflowQueueView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "list.bullet.clipboard")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Queue")
                .font(.title)

            Text("Active work items and available queue will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowDashboardView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.bar")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Dashboard")
                .font(.title)

            Text("Starred and recent workflows will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowBuilderView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.and.pencil")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Builder")
                .font(.title)

            Text("Visual workflow canvas will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowDesignerView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "paintbrush")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Designer")
                .font(.title)

            Text("Stage list and editor will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct WorkflowAnalyticsView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chart.line.uptrend.xyaxis")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("Workflow Analytics")
                .font(.title)

            Text("Metrics and stage performance will appear here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
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
