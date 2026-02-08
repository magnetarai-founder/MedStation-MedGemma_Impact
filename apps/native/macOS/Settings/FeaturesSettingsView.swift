//
//  FeaturesSettingsView.swift
//  MagnetarStudio (macOS)
//
//  Phase 2D: Feature toggles for power workspaces
//  Users can enable/disable optional features here
//

import SwiftUI

struct FeaturesSettingsView: View {
    private var featureFlags: FeatureFlags { FeatureFlags.shared }

    var body: some View {
        Form {
            // Header
            Section {
                HStack(spacing: 12) {
                    Image(systemName: "puzzlepiece.extension.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Features")
                            .font(.title2.bold())
                        Text("Enable power workspaces and optional features")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 8)
            }

            // Power Workspaces
            Section {
                FeatureToggleRow(
                    icon: "chevron.left.forwardslash.chevron.right",
                    title: "Code Workspace",
                    description: "Full IDE with syntax highlighting, git integration, and AI assistance",
                    isOn: Binding(
                        get: { featureFlags.code },
                        set: { featureFlags.code = $0 }
                    ),
                    color: .purple
                )

                FeatureToggleRow(
                    icon: "tablecells",
                    title: "Database & Data Analysis",
                    description: "SQL query builder, data visualization, and spreadsheet tools",
                    isOn: Binding(
                        get: { featureFlags.dataAnalysis },
                        set: { featureFlags.dataAnalysis = $0 }
                    ),
                    color: .blue
                )

                FeatureToggleRow(
                    icon: "rectangle.3.group",
                    title: "Project Management",
                    description: "Kanban boards, task tracking, and project organization",
                    isOn: Binding(
                        get: { featureFlags.projectManagement },
                        set: { featureFlags.projectManagement = $0 }
                    ),
                    color: .green
                )

                FeatureToggleRow(
                    icon: "waveform",
                    title: "Voice & Insights",
                    description: "Voice transcription, meeting notes, and audio analysis",
                    isOn: Binding(
                        get: { featureFlags.voiceTranscription },
                        set: { featureFlags.voiceTranscription = $0 }
                    ),
                    color: .orange
                )
            } header: {
                Text("Power Workspaces")
            } footer: {
                Text("Power workspaces open in separate windows via the + menu or keyboard shortcuts")
            }

            // Collaboration Features
            Section {
                FeatureToggleRow(
                    icon: "person.2.fill",
                    title: "Team Collaboration",
                    description: "Real-time collaboration, channels, and direct messages — coming in a future update",
                    isOn: .constant(false),
                    color: .cyan,
                    badge: "Coming Soon",
                    disabled: true
                )
            } header: {
                Text("Collaboration")
            }

            // Special Features
            Section {
                FeatureToggleRow(
                    icon: "hands.sparkles.fill",
                    title: "MagnetarTrust",
                    description: "Trust network for churches, missions, and faith-based organizations",
                    isOn: Binding(
                        get: { featureFlags.trust },
                        set: { featureFlags.trust = $0 }
                    ),
                    color: .pink
                )

                FeatureToggleRow(
                    icon: "building.2.fill",
                    title: "MagnetarHub",
                    description: "Admin dashboard and organization management",
                    isOn: Binding(
                        get: { featureFlags.magnetarHub },
                        set: { featureFlags.magnetarHub = $0 }
                    ),
                    color: .indigo,
                    badge: "Admin"
                )
            } header: {
                Text("Special Features")
            }

            // Quick Actions
            Section {
                HStack(spacing: 12) {
                    Button("Enable All") {
                        withAnimation {
                            featureFlags.enableAll()
                        }
                    }
                    .buttonStyle(.bordered)

                    Button("Reset to Defaults") {
                        withAnimation {
                            featureFlags.resetToDefaults()
                        }
                    }
                    .buttonStyle(.bordered)
                    .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
        .formStyle(.grouped)
        .frame(minWidth: 450)
    }
}

// MARK: - Feature Toggle Row

private struct FeatureToggleRow: View {
    let icon: String
    let title: String
    let description: String
    @Binding var isOn: Bool
    var color: Color = .accentColor
    var badge: String? = nil
    var disabled: Bool = false

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 14) {
            // Icon
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(color.opacity(disabled ? 0.08 : 0.15))
                    .frame(width: 36, height: 36)

                Image(systemName: icon)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(disabled ? .secondary : color)
            }

            // Text
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(disabled ? .secondary : .primary)

                    if let badge = badge {
                        Text(badge)
                            .font(.system(size: 9, weight: .semibold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule()
                                    .fill(disabled ? Color.gray.opacity(0.6) : color.opacity(0.8))
                            )
                    }
                }

                Text(description)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            // Toggle
            Toggle("", isOn: $isOn)
                .toggleStyle(.switch)
                .controlSize(.small)
                .disabled(disabled)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
        .onTapGesture {
            guard !disabled else { return }
            withAnimation(.easeInOut(duration: 0.2)) {
                isOn.toggle()
            }
        }
    }
}

// MARK: - Preview

#Preview {
    FeaturesSettingsView()
        .frame(width: 550, height: 700)
}
