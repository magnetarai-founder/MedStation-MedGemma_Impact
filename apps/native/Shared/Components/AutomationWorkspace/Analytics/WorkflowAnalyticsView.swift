//
//  WorkflowAnalyticsView.swift
//  MagnetarStudio
//
//  Main analytics view showing workflow metrics and performance
//

import SwiftUI

struct WorkflowAnalyticsView: View {
    @State private var analytics: LegacyWorkflowAnalytics = LegacyWorkflowAnalytics.mock

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Primary metrics grid
                LazyVGrid(columns: metricsColumns, spacing: 16) {
                    MetricCard(
                        title: "Total Items",
                        value: "\(analytics.totalItems)",
                        icon: "square.stack.3d.up",
                        color: .blue
                    )

                    MetricCard(
                        title: "Completed",
                        value: "\(analytics.completedItems)",
                        subtitle: "\(analytics.completionPercent)%",
                        icon: "checkmark.circle.fill",
                        color: .green
                    )

                    MetricCard(
                        title: "In Progress",
                        value: "\(analytics.inProgressItems)",
                        icon: "arrow.triangle.2.circlepath",
                        color: .orange
                    )

                    MetricCard(
                        title: "Avg Cycle Time",
                        value: analytics.avgCycleTime,
                        subtitle: analytics.medianCycleTime != nil ? "Median: \(analytics.medianCycleTime!)" : nil,
                        icon: "clock",
                        color: .purple
                    )
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // Extra status metrics
                if analytics.cancelledItems > 0 || analytics.failedItems > 0 {
                    LazyVGrid(columns: extraMetricsColumns, spacing: 16) {
                        if analytics.cancelledItems > 0 {
                            MetricCard(
                                title: "Cancelled",
                                value: "\(analytics.cancelledItems)",
                                icon: "xmark.circle",
                                color: .gray,
                                isCompact: true
                            )
                        }

                        if analytics.failedItems > 0 {
                            MetricCard(
                                title: "Failed",
                                value: "\(analytics.failedItems)",
                                icon: "exclamationmark.triangle.fill",
                                color: .red,
                                isCompact: true
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                }

                // Stage Performance Table
                VStack(alignment: .leading, spacing: 12) {
                    Text("Stage Performance")
                        .font(.system(size: 18, weight: .semibold))
                        .padding(.horizontal, 16)

                    StagePerformanceTable(stages: analytics.stagePerformance)
                }
            }
            .padding(.bottom, 24)
        }
    }

    private var metricsColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16)
        ]
    }

    private var extraMetricsColumns: [GridItem] {
        [
            GridItem(.flexible(), spacing: 16),
            GridItem(.flexible(), spacing: 16)
        ]
    }
}
