//
//  Colors.swift
//  MagnetarStudio
//
//  Liquid Glass color system for macOS 26 / iPadOS 26.
//  Adaptive colors that work in light and dark mode.
//

import SwiftUI
#if os(macOS)
import AppKit
#endif

extension Color {
    // MARK: - Brand Colors

    /// Magnetar Primary - Electric Blue (#3B82F6)
    static let magnetarPrimary = Color(red: 0.231, green: 0.510, blue: 0.965)

    /// Magnetar Secondary - Purple (#A855F7)
    static let magnetarSecondary = Color(red: 0.659, green: 0.333, blue: 0.969)

    /// Magnetar Accent - Cyan (#06B6D4)
    static let magnetarAccent = Color(red: 0.024, green: 0.714, blue: 0.831)

    // MARK: - Liquid Glass Materials

    /// Ultra-thin glass material (most transparent)
    static let glassUltraThin: Color = {
        #if os(macOS)
        return Color(nsColor: .windowBackgroundColor).opacity(0.3)
        #else
        return Color(.systemBackground).opacity(0.3)
        #endif
    }()

    /// Regular glass material (balanced transparency)
    static let glassRegular: Color = {
        #if os(macOS)
        return Color(nsColor: .windowBackgroundColor).opacity(0.5)
        #else
        return Color(.systemBackground).opacity(0.5)
        #endif
    }()

    /// Thick glass material (more opaque)
    static let glassThick: Color = {
        #if os(macOS)
        return Color(nsColor: .windowBackgroundColor).opacity(0.7)
        #else
        return Color(.systemBackground).opacity(0.7)
        #endif
    }()

    // MARK: - Semantic Colors

    static let textPrimary = Color.primary
    static let textSecondary = Color.secondary
    static let textTertiary: Color = {
        #if os(macOS)
        return Color(nsColor: .tertiaryLabelColor)
        #else
        return Color(.tertiaryLabel)
        #endif
    }()

    static let success = Color.green
    static let error = Color.red
    static let warning = Color.orange
    static let info = Color.blue

    // MARK: - Surface Colors

    static let surfacePrimary: Color = {
        #if os(macOS)
        return Color(nsColor: .windowBackgroundColor)
        #else
        return Color(.systemBackground)
        #endif
    }()

    static let surfaceSecondary: Color = {
        #if os(macOS)
        return Color(nsColor: .controlBackgroundColor)
        #else
        return Color(.secondarySystemBackground)
        #endif
    }()

    static let surfaceTertiary: Color = {
        #if os(macOS)
        return Color(nsColor: .underPageBackgroundColor)
        #else
        return Color(.tertiarySystemBackground)
        #endif
    }()
}

// MARK: - Gradient Helpers

extension LinearGradient {
    /// Magnetar brand gradient
    static let magnetarGradient = LinearGradient(
        colors: [Color.magnetarPrimary, Color.magnetarSecondary],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Glass shimmer effect
    static let glassShimmer = LinearGradient(
        colors: [
            Color.white.opacity(0.2),
            Color.white.opacity(0.1),
            Color.white.opacity(0.2)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

// MARK: - Animation Constants

extension Animation {
    /// Quick animation for UI state changes (150ms)
    static let magnetarQuick = Animation.easeInOut(duration: 0.15)

    /// Standard animation for most UI transitions (200ms)
    static let magnetarStandard = Animation.easeInOut(duration: 0.2)

    /// Smooth animation for larger transitions (300ms)
    static let magnetarSmooth = Animation.easeInOut(duration: 0.3)

    /// Spring animation for interactive elements (hover, press)
    static let magnetarSpring = Animation.spring(response: 0.3, dampingFraction: 0.7)

    /// Gentle spring for subtle interactive feedback
    static let magnetarGentleSpring = Animation.spring(response: 0.25, dampingFraction: 0.8)
}

extension AnyTransition {
    /// Standard fade transition
    static let magnetarFade = AnyTransition.opacity.animation(.magnetarQuick)

    /// Slide from trailing edge
    static let magnetarSlideTrailing = AnyTransition.move(edge: .trailing)
        .combined(with: .opacity)
        .animation(.magnetarStandard)

    /// Slide from bottom edge
    static let magnetarSlideBottom = AnyTransition.move(edge: .bottom)
        .combined(with: .opacity)
        .animation(.magnetarStandard)

    /// Scale and fade
    static let magnetarScale = AnyTransition.scale(scale: 0.95)
        .combined(with: .opacity)
        .animation(.magnetarSmooth)
}
