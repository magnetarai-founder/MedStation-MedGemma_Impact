//
//  KanbanWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Kanban task management workspace (placeholder).
//

import SwiftUI

struct KanbanWorkspace: View {
    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .opacity(0.1)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                Image(systemName: "square.grid.2x2")
                    .font(.system(size: 64))
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("Kanban Workspace")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Task management coming soon")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    KanbanWorkspace()
}
