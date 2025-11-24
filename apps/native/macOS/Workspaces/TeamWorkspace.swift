//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace (placeholder).
//

import SwiftUI

struct TeamWorkspace: View {
    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .opacity(0.1)
                .ignoresSafeArea()

            VStack(spacing: 20) {
                Image(systemName: "person.2")
                    .font(.system(size: 64))
                    .foregroundStyle(LinearGradient.magnetarGradient)

                Text("Team Workspace")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Team collaboration coming soon")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }
        }
    }
}

#Preview {
    TeamWorkspace()
}
