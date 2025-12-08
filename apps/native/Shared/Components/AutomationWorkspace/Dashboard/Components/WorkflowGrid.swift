//
//  WorkflowGrid.swift
//  MagnetarStudio
//
//  Grid layout for workflow cards in the dashboard
//

import SwiftUI

// MARK: - Workflow Grid

struct WorkflowGrid: View {
    let workflows: [WorkflowCard]
    let showStarByDefault: Bool

    var body: some View {
        LazyVGrid(columns: gridColumns, spacing: 16) {
            ForEach(workflows) { workflow in
                WorkflowCardView(workflow: workflow, showStarByDefault: showStarByDefault)
            }
        }
        .padding(.horizontal, 16)
    }

    private var gridColumns: [GridItem] {
        [GridItem(.adaptive(minimum: 280, maximum: 360), spacing: 16)]
    }
}
