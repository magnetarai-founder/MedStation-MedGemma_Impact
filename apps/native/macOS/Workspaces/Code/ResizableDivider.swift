//
//  ResizableDivider.swift
//  MagnetarStudio
//
//  Draggable divider for resizing panes in the Coding workspace.
//  Supports horizontal and vertical axes with min/max constraints
//  and double-click-to-reset behavior.
//

import SwiftUI

/// A draggable divider that resizes an adjacent pane
struct ResizableDivider: View {
    @Binding var dimension: Double
    let axis: Axis
    let minValue: Double
    let maxValue: Double
    let defaultValue: Double
    var invertDrag: Bool = false

    @State private var isDragging: Bool = false

    var body: some View {
        Group {
            if axis == .horizontal {
                horizontalDivider
            } else {
                verticalDivider
            }
        }
    }

    private var horizontalDivider: some View {
        Rectangle()
            .fill(isDragging ? Color.magnetarPrimary.opacity(0.5) : Color.clear)
            .frame(width: 6)
            .overlay {
                Rectangle()
                    .fill(Color.gray.opacity(isDragging ? 0.6 : 0.3))
                    .frame(width: 1)
            }
            .contentShape(Rectangle())
            .cursor(.resizeLeftRight)
            .gesture(
                DragGesture(minimumDistance: 1)
                    .onChanged { value in
                        isDragging = true
                        let delta = invertDrag ? -value.translation.width : value.translation.width
                        let newValue = dimension + Double(delta)
                        dimension = min(maxValue, max(minValue, newValue))
                    }
                    .onEnded { _ in
                        isDragging = false
                    }
            )
            .onTapGesture(count: 2) {
                withAnimation(.magnetarQuick) {
                    dimension = defaultValue
                }
            }
    }

    private var verticalDivider: some View {
        Rectangle()
            .fill(isDragging ? Color.magnetarPrimary.opacity(0.5) : Color.clear)
            .frame(height: 6)
            .overlay {
                Rectangle()
                    .fill(Color.gray.opacity(isDragging ? 0.6 : 0.3))
                    .frame(height: 1)
            }
            .contentShape(Rectangle())
            .cursor(.resizeUpDown)
            .gesture(
                DragGesture(minimumDistance: 1)
                    .onChanged { value in
                        isDragging = true
                        let delta = invertDrag ? -value.translation.height : value.translation.height
                        let newValue = dimension + Double(delta)
                        dimension = min(maxValue, max(minValue, newValue))
                    }
                    .onEnded { _ in
                        isDragging = false
                    }
            )
            .onTapGesture(count: 2) {
                withAnimation(.magnetarQuick) {
                    dimension = defaultValue
                }
            }
    }
}

// cursor() extension is defined in DatabaseComponents.swift
