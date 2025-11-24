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
