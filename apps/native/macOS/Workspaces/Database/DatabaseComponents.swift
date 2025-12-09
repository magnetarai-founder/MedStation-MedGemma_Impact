//
//  DatabaseComponents.swift
//  MagnetarStudio (macOS)
//
//  Supporting UI components for Database Workspace:
//  - IconToolbarButton
//  - DragHandle
//  - Cursor extension
//

import SwiftUI

// MARK: - Icon Toolbar Button

struct IconToolbarButton: View {
    let icon: String
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(isHovered ? Color.magnetarPrimary : .secondary)
                .frame(width: 32, height: 32)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isHovered ? Color.white.opacity(0.6) : Color.clear)
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.magnetarStandard) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Drag Handle

struct DragHandle: View {
    @State private var isHovered = false
    @State private var isDragging = false

    var body: some View {
        ZStack {
            // Background bar
            Rectangle()
                .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                .opacity(isDragging ? 1.0 : 0.5)

            // Grip icon (on hover)
            if isHovered || isDragging {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                    )
            }
        }
        .frame(maxWidth: .infinity)
        .contentShape(Rectangle()) // Make entire area draggable
        .onHover { hovering in
            isHovered = hovering
        }
        .gesture(
            DragGesture()
                .onChanged { _ in
                    isDragging = true
                }
                .onEnded { _ in
                    isDragging = false
                }
        )
        .cursor(.resizeUpDown)
    }
}

// MARK: - Cursor Extension

extension View {
    func cursor(_ cursor: NSCursor) -> some View {
        self.onContinuousHover { phase in
            switch phase {
            case .active:
                cursor.push()
            case .ended:
                NSCursor.pop()
            }
        }
    }
}
