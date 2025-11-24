//
//  DatabaseWorkspace.swift
//  MagnetarStudio (macOS)
//
//  SQL query workspace (placeholder).
//

import SwiftUI

struct DatabaseWorkspace: View {
    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .opacity(0.1)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                Image(systemName: "cylinder")
                    .font(.system(size: 64))
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("Database Workspace")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("SQL query interface coming soon")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    DatabaseWorkspace()
}
