//
//  LoadingView.swift
//  MagnetarStudio
//
//  Loading screen shown during auth validation (.checking state)
//

import SwiftUI

struct LoadingView: View {
    let message: String

    var body: some View {
        ZStack {
            LinearGradient.magnetarGradient
                .ignoresSafeArea()

            VStack(spacing: 24) {
                ProgressView()
                    .scaleEffect(2.0)
                    .tint(.white)

                Text(message)
                    .font(.headline)
                    .foregroundStyle(.white)
            }
        }
    }
}

// MARK: - Preview

#Preview {
    LoadingView(message: "Checking authentication...")
        .frame(width: 1200, height: 800)
}
