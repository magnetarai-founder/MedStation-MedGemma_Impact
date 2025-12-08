//
//  WorkflowBuilderView.swift
//  MagnetarStudio
//
//  Visual workflow builder with node-based canvas
//

import SwiftUI

struct WorkflowBuilderView: View {
    @State private var workflowTitle: String = "Customer Onboarding Flow"
    @State private var isEditingTitle: Bool = false
    @State private var isRunning: Bool = false
    @State private var showInfoPanel: Bool = false
    @State private var showHelpPanel: Bool = false
    @State private var isHoveringTitle: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            builderHeader
                .padding(.horizontal, 24)
                .padding(.vertical, 16)
                .background(Color(.controlBackgroundColor))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Canvas with floating controls
            ZStack(alignment: .bottomTrailing) {
                canvasArea

                // Bottom-right: Info controls
                VStack(alignment: .trailing, spacing: 12) {
                    if showInfoPanel {
                        infoPanel
                    }

                    floatingButton(
                        icon: "info.circle",
                        isActive: showInfoPanel,
                        action: { showInfoPanel.toggle() }
                    )
                }
                .padding(.trailing, 20)
                .padding(.bottom, 160)

                // Bottom-left: Help panel
                VStack(alignment: .leading, spacing: 12) {
                    if showHelpPanel {
                        helpPanel
                    }

                    floatingButton(
                        icon: "questionmark.circle",
                        isActive: showHelpPanel,
                        action: { showHelpPanel.toggle() }
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.leading, 24)
                .padding(.bottom, 24)
            }
        }
    }

    // MARK: - Header

    private var builderHeader: some View {
        HStack(spacing: 12) {
            // Back button
            Button {
                // Navigate back
            } label: {
                Image(systemName: "arrow.left")
                    .font(.system(size: 20))
                    .foregroundColor(.primary)
                    .frame(width: 40, height: 40)
            }
            .buttonStyle(.plain)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.0))
            )
            .onHover { hovering in
                // Hover effect
            }

            // Title block
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 8) {
                    if isEditingTitle {
                        TextField("", text: $workflowTitle)
                            .font(.system(size: 20, weight: .semibold))
                            .textFieldStyle(.plain)
                            .overlay(
                                Rectangle()
                                    .fill(Color.magnetarPrimary)
                                    .frame(height: 2),
                                alignment: .bottom
                            )
                            .onSubmit {
                                isEditingTitle = false
                            }
                    } else {
                        Text(workflowTitle)
                            .font(.system(size: 20, weight: .semibold))
                            .onTapGesture {
                                isEditingTitle = true
                            }
                            .onHover { hovering in
                                isHoveringTitle = hovering
                            }

                        if isHoveringTitle {
                            Image(systemName: "pencil")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                        }
                    }
                }

                Text("Drag nodes to customize your workflow")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Right: Save + Run buttons
            HStack(spacing: 8) {
                Button {
                    // Save workflow
                } label: {
                    Image(systemName: "square.and.arrow.down")
                        .font(.system(size: 20))
                        .foregroundColor(.primary)
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )

                Button {
                    isRunning.toggle()
                } label: {
                    Image(systemName: "play.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.white)
                        .frame(width: 40, height: 40)
                }
                .buttonStyle(.plain)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.magnetarPrimary)
                )
                .opacity(isRunning ? 0.6 : 1.0)
                .animation(isRunning ? Animation.easeInOut(duration: 1.0).repeatForever() : .default, value: isRunning)
            }
        }
    }

    // MARK: - Canvas

    private var canvasArea: some View {
        ZStack {
            // Dot background
            DotPattern()

            // Canvas content
            VStack(spacing: 16) {
                Image(systemName: "square.grid.3x2")
                    .font(.system(size: 64))
                    .foregroundColor(.secondary)

                Text("Workflow Canvas")
                    .font(.title)

                Text("ReactFlow-style node editor will render here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            // Minimap (top-right corner)
            VStack {
                HStack {
                    Spacer()

                    VStack(spacing: 8) {
                        Text("MiniMap")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.gray.opacity(0.3))
                            .frame(width: 120, height: 80)
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(.controlBackgroundColor))
                            .shadow(color: Color.black.opacity(0.1), radius: 4, x: 0, y: 2)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                    .padding(16)
                }

                Spacer()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Floating Controls

    private func floatingButton(icon: String, isActive: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(isActive ? Color.magnetarPrimary : .primary)
                .frame(width: 40, height: 40)
        }
        .buttonStyle(.plain)
        .background(
            Circle()
                .fill(isActive ? Color.magnetarPrimary.opacity(0.1) : Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            Circle()
                .strokeBorder(isActive ? Color.magnetarPrimary.opacity(0.3) : Color.gray.opacity(0.2), lineWidth: 1)
        )
        .scaleEffect(1.0)
        .animation(.easeInOut(duration: 0.2), value: isActive)
    }

    private var infoPanel: some View {
        VStack(spacing: 0) {
            // Header
            Text("Zoom Controls")
                .font(.system(size: 14, weight: .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.gray.opacity(0.03))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Zoom buttons
            VStack(spacing: 0) {
                controlButton(icon: "plus.magnifyingglass", label: "Zoom In")
                controlButton(icon: "minus.magnifyingglass", label: "Zoom Out")
                controlButton(icon: "arrow.up.left.and.arrow.down.right", label: "Fit View")
            }
            .padding(12)
        }
        .frame(width: 200)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    private var helpPanel: some View {
        VStack(spacing: 0) {
            // Header
            Text("Node Types")
                .font(.system(size: 14, weight: .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(Color.gray.opacity(0.03))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Legend items
            VStack(alignment: .leading, spacing: 12) {
                legendRow(color: .green, label: "Trigger")
                legendRow(color: .blue, label: "Action")
                legendRow(color: .purple, label: "AI Stage")
                legendRow(color: .orange, label: "Output")
            }
            .padding(16)
        }
        .frame(width: 280)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    private func controlButton(icon: String, label: String) -> some View {
        Button {
            // Zoom action
        } label: {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(.primary)
                    .frame(width: 20)

                Text(label)
                    .font(.system(size: 14))
                    .foregroundColor(.primary)

                Spacer()
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.clear)
        )
        .onHover { hovering in
            // Hover effect
        }
    }

    private func legendRow(color: Color, label: String) -> some View {
        HStack(spacing: 10) {
            Circle()
                .fill(color)
                .frame(width: 12, height: 12)

            Text(label)
                .font(.system(size: 14))
                .foregroundColor(.secondary)

            Spacer()
        }
    }
}
