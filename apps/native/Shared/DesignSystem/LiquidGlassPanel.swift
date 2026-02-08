//
//  LiquidGlassPanel.swift
//  MagnetarStudio
//
//  Liquid Glass panel component - core building block of the UI.
//  Provides blur, refraction, and dynamic tinting.
//

import SwiftUI

struct LiquidGlassPanel<Content: View>: View {
    let content: Content
    let material: GlassMaterial
    let cornerRadius: CGFloat
    let shadowRadius: CGFloat

    init(
        material: GlassMaterial = .regular,
        cornerRadius: CGFloat = 16,
        shadowRadius: CGFloat = 20,
        @ViewBuilder content: () -> Content
    ) {
        self.content = content()
        self.material = material
        self.cornerRadius = cornerRadius
        self.shadowRadius = shadowRadius
    }

    var body: some View {
        content
            .padding()
            .background(material.swiftUIMaterial)
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            .shadow(color: .black.opacity(0.1), radius: shadowRadius, y: 10)
    }
}

// MARK: - Glass Material Types

enum GlassMaterial {
    case ultraThin
    case thin
    case regular
    case thick

    var swiftUIMaterial: Material {
        switch self {
        case .ultraThin: return .ultraThinMaterial
        case .thin: return .thinMaterial
        case .regular: return .regularMaterial
        case .thick: return .thickMaterial
        }
    }
}

// MARK: - Glass Background View Modifier (macOS Tahoe Style)

struct GlassBackgroundModifier: ViewModifier {
    let material: GlassMaterial
    @AppStorage("glassOpacity") private var glassOpacity = 0.5

    func body(content: Content) -> some View {
        content
            .background(
                // macOS Tahoe Liquid Glass: material + opacity control
                material.swiftUIMaterial
                    .opacity(glassOpacity)
            )
    }
}

extension View {
    func glassBackground(material: GlassMaterial = .regular) -> some View {
        modifier(GlassBackgroundModifier(material: material))
    }

    /// macOS Tahoe-style transparent navigation glass
    /// Refracts content behind it while reflecting wallpaper
    func navigationGlass() -> some View {
        modifier(GlassBackgroundModifier(material: .ultraThin))
    }

    /// macOS Tahoe-style header/toolbar glass
    /// Completely transparent with subtle material
    func headerGlass() -> some View {
        modifier(GlassBackgroundModifier(material: .thin))
    }
}

// MARK: - Preview

#Preview {
    ZStack {
        // Background gradient
        LinearGradient.magnetarGradient
            .ignoresSafeArea()

        VStack(spacing: 20) {
            LiquidGlassPanel(material: .ultraThin) {
                VStack(alignment: .leading) {
                    Text("Ultra Thin Glass")
                        .font(.headline)
                    Text("Most transparent layer")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            LiquidGlassPanel(material: .regular) {
                VStack(alignment: .leading) {
                    Text("Regular Glass")
                        .font(.headline)
                    Text("Balanced transparency")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            LiquidGlassPanel(material: .thick) {
                VStack(alignment: .leading) {
                    Text("Thick Glass")
                        .font(.headline)
                    Text("More opaque, stronger backdrop")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
    }
}
