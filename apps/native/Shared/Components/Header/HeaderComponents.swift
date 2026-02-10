//
//  HeaderComponents.swift
//  MedStation
//
//  Reusable header UI components.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "HeaderComponents")

// MARK: - Header Toolbar Button

struct HeaderToolbarButton: View {
    let icon: String
    var label: String? = nil
    var tint: Color = .secondary
    var background: Color = Color.white.opacity(0.08)
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(tint)

                if let label {
                    Text(label)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(tint)
                }
            }
            .padding(.horizontal, label != nil ? 10 : 8)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(isHovered ? background.opacity(1.5) : background)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
