//
//  Header.swift
//  MedStation
//
//  Simplified header for MedStation.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "Header")

struct Header: View {
    var body: some View {
        ZStack(alignment: .center) {
            // Background
            Color(.windowBackgroundColor).opacity(0.94)
                .headerGlass()
                .ignoresSafeArea(edges: .top)

            HStack(alignment: .center, spacing: 16) {
                Text("MedStation")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(.primary)

                Spacer()

                // Model status indicator
                ModelStatusIndicator()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
        }
        .frame(height: 54)
    }
}

// MARK: - Model Status Indicator

private struct ModelStatusIndicator: View {
    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Color.green)
                .frame(width: 8, height: 8)

            Text("MedGemma")
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
        }
    }
}

#Preview {
    Header()
        .frame(width: 1200)
}
