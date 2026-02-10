//
//  GlassButton.swift
//  MedStation
//
//  Liquid Glass button with hover effects and haptic feedback.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "GlassButton")

struct GlassButton: View {
    let title: String
    let icon: String?
    let style: ButtonStyle
    let action: () -> Void

    @State private var isHovered = false

    init(
        _ title: String,
        icon: String? = nil,
        style: ButtonStyle = .primary,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.style = style
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let icon = icon {
                    Image(systemName: icon)
                }
                Text(title)
                    .fontWeight(.medium)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .padding(.horizontal, 20)
            .background(backgroundView)
            .foregroundStyle(foregroundColor)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .shadow(color: shadowColor, radius: isHovered ? 12 : 8, y: 4)
            .scaleEffect(isHovered ? 1.02 : 1.0)
            .animation(.medstationSpring, value: isHovered)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    @ViewBuilder
    private var backgroundView: some View {
        switch style {
        case .primary:
            LinearGradient.medstationGradient
                .opacity(isHovered ? 1.0 : 0.9)

        case .secondary:
            Color.glassRegular
                .overlay(.ultraThinMaterial)

        case .destructive:
            LinearGradient(
                colors: [Color.red, Color.red.opacity(0.8)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .opacity(isHovered ? 1.0 : 0.9)

        case .ghost:
            Color.clear
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.primary.opacity(0.2), lineWidth: 1)
                )
        }
    }

    private var foregroundColor: Color {
        switch style {
        case .primary, .destructive:
            return .white
        case .secondary, .ghost:
            return .primary
        }
    }

    private var shadowColor: Color {
        switch style {
        case .primary:
            return Color.medstationPrimary.opacity(0.3)
        case .destructive:
            return Color.red.opacity(0.3)
        case .secondary, .ghost:
            return Color.black.opacity(0.1)
        }
    }

    enum ButtonStyle {
        case primary
        case secondary
        case destructive
        case ghost
    }
}

// MARK: - Preview

#Preview {
    ZStack {
        LinearGradient.medstationGradient
            .ignoresSafeArea()

        VStack(spacing: 20) {
            GlassButton("Sign In", icon: "person.fill", style: .primary) {
                logger.debug("Sign in tapped")
            }

            GlassButton("Cancel", style: .secondary) {
                logger.debug("Cancel tapped")
            }

            GlassButton("Delete", icon: "trash", style: .destructive) {
                logger.debug("Delete tapped")
            }

            GlassButton("Learn More", style: .ghost) {
                logger.debug("Learn more tapped")
            }
        }
        .padding()
        .frame(width: 300)
    }
}
