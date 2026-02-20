//
//  Colors.swift
//  MedStation
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

    /// MedStation Primary - Electric Blue (#3B82F6)
    static let medstationPrimary = Color(red: 0.231, green: 0.510, blue: 0.965)

    /// MedStation Secondary - Purple (#A855F7)
    static let medstationSecondary = Color(red: 0.659, green: 0.333, blue: 0.969)

    // MARK: - Liquid Glass Materials

    /// Regular glass material (balanced transparency)
    static let glassRegular: Color = {
        #if os(macOS)
        return Color(nsColor: .windowBackgroundColor).opacity(0.5)
        #else
        return Color(.systemBackground).opacity(0.5)
        #endif
    }()

    // MARK: - Semantic Colors

    static let textPrimary = Color.primary
    static let textSecondary = Color.secondary

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
    /// MedStation brand gradient
    static let medstationGradient = LinearGradient(
        colors: [Color.medstationPrimary, Color.medstationSecondary],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

// MARK: - Animation Constants

extension Animation {
    /// Spring animation for interactive elements (hover, press)
    static let medstationSpring = Animation.spring(response: 0.3, dampingFraction: 0.7)
}
