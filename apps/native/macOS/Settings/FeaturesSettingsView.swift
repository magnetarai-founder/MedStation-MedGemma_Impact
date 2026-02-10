//
//  FeaturesSettingsView.swift
//  MedStation
//
//  Feature toggles for MedStation.
//

import SwiftUI

struct FeaturesSettingsView: View {
    private var featureFlags: FeatureFlags { FeatureFlags.shared }

    var body: some View {
        Form {
            Section {
                HStack(spacing: 12) {
                    Image(systemName: "cross.case.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(LinearGradient.medstationGradient)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Features")
                            .font(.title2.bold())
                        Text("Configure MedStation capabilities")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 8)
            }

            Section {
                FeatureToggleRow(
                    icon: "stethoscope",
                    title: "Medical AI",
                    description: "5-step agentic workflow with MedGemma for clinical decision support",
                    isOn: .constant(true),
                    color: .green,
                    badge: "Core",
                    disabled: true
                )

                FeatureToggleRow(
                    icon: "person.2.fill",
                    title: "Team Collaboration",
                    description: "Share cases and collaborate with clinical teams — coming soon",
                    isOn: Binding(
                        get: { featureFlags.team },
                        set: { featureFlags.team = $0 }
                    ),
                    color: .cyan,
                    badge: "Coming Soon",
                    disabled: true
                )
            } header: {
                Text("Capabilities")
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

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(color.opacity(disabled ? 0.08 : 0.15))
                    .frame(width: 36, height: 36)

                Image(systemName: icon)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(disabled ? .secondary : color)
            }

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

            Toggle("", isOn: $isOn)
                .toggleStyle(.switch)
                .controlSize(.small)
                .disabled(disabled)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    FeaturesSettingsView()
        .frame(width: 550, height: 400)
}
