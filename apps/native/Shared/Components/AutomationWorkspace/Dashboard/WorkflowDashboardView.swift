//
//  WorkflowDashboardView.swift
//  MagnetarStudio
//
//  Main dashboard view for workflows with starred and recent sections
//

import SwiftUI

struct WorkflowDashboardView: View {
    @State private var scopeFilter: DashboardScope = .all
    @State private var starredWorkflows: [WorkflowCard] = []
    @State private var recentWorkflows: [WorkflowCard] = []
    @State private var isLoading: Bool = false
    @State private var error: String? = nil

    private let workflowService = WorkflowService.shared

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Scope filter + count
                HStack(spacing: 12) {
                    Menu {
                        Button("All Workflows") { scopeFilter = .all }
                        Button("My Workflows") { scopeFilter = .my }
                        Button("Team Workflows") { scopeFilter = .team }
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "line.3.horizontal.decrease.circle")
                                .font(.system(size: 16))

                            Text(scopeFilter.displayName)
                                .font(.system(size: 14))

                            Image(systemName: "chevron.down")
                                .font(.system(size: 10))
                        }
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.gray.opacity(0.1))
                        )
                    }
                    .buttonStyle(.plain)

                    Text("\(starredWorkflows.count + recentWorkflows.count) workflows")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)

                    Spacer()

                    // Action buttons
                    HStack(spacing: 8) {
                        Button {
                            // Browse templates
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "doc.text.magnifyingglass")
                                    .font(.system(size: 16))
                                Text("Browse Templates")
                                    .font(.system(size: 14, weight: .medium))
                            }
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.orange)
                            )
                        }
                        .buttonStyle(.plain)

                        Button {
                            // Create workflow
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "plus")
                                    .font(.system(size: 16))
                                Text("Create")
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
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // Starred section
                if !starredWorkflows.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Image(systemName: "star.fill")
                                .font(.system(size: 16))
                                .foregroundColor(.orange)
                            Text("Starred")
                                .font(.system(size: 18, weight: .semibold))
                        }
                        .padding(.horizontal, 16)

                        WorkflowGrid(workflows: starredWorkflows, showStarByDefault: true)
                    }
                }

                // Agent CTA card
                AgentAssistCard()
                    .padding(.horizontal, 16)

                // Recent section
                if !recentWorkflows.isEmpty {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Image(systemName: "clock")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                            Text("Recent")
                                .font(.system(size: 18, weight: .semibold))
                        }
                        .padding(.horizontal, 16)

                        WorkflowGrid(workflows: recentWorkflows, showStarByDefault: false)
                    }
                }
            }
            .padding(.bottom, 24)
        }
        .task {
            await loadWorkflows()
        }
    }

    // MARK: - Data Loading

    @MainActor
    private func loadWorkflows() async {
        isLoading = true
        error = nil

        do {
            // Load workflows from backend
            let allWorkflows = try await workflowService.listWorkflows(type: "all")

            // Convert Workflow models to WorkflowCard models
            // For now, show all as "recent" until we have starred/favoriting logic
            recentWorkflows = allWorkflows.map { workflow in
                WorkflowCard(
                    name: workflow.name,
                    description: workflow.description ?? "",
                    icon: workflow.icon ?? "gearshape.2",
                    typeName: workflow.category ?? workflow.workflowType ?? "General",
                    typeColor: colorForCategory(workflow.category ?? "general"),
                    isTemplate: workflow.isTemplate ?? false,
                    visibility: visibilityFromString(workflow.visibility ?? "private")
                )
            }

            // For now, starred is empty - would need backend support for favoriting
            starredWorkflows = []
        } catch {
            print("Failed to load workflows: \(error)")
            self.error = "Failed to load workflows"
            // Keep empty arrays on error
        }

        isLoading = false
    }

    // Helper functions
    private func colorForCategory(_ category: String) -> Color {
        switch category.lowercased() {
        case "onboarding": return .green
        case "finance": return .blue
        case "support": return .orange
        case "data": return .purple
        case "content": return .pink
        case "security": return .red
        case "devops": return .cyan
        default: return .blue
        }
    }

    private func visibilityFromString(_ visibility: String) -> WorkflowVisibility {
        switch visibility.lowercased() {
        case "personal", "private": return .private
        case "team": return .team
        case "global", "public": return .public
        default: return .private
        }
    }
}
