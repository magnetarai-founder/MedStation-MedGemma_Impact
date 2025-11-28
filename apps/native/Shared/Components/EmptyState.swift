//
//  EmptyState.swift
//  MagnetarStudio
//
//  Reusable empty state component with consistent styling
//

import SwiftUI

struct EmptyState: View {
    let icon: String
    let title: String
    let message: String?
    let action: (() -> Void)?
    let actionLabel: String?

    init(
        icon: String,
        title: String,
        message: String? = nil,
        action: (() -> Void)? = nil,
        actionLabel: String? = nil
    ) {
        self.icon = icon
        self.title = title
        self.message = message
        self.action = action
        self.actionLabel = actionLabel
    }

    var body: some View {
        VStack(spacing: 20) {
            // Icon
            Image(systemName: icon)
                .font(.system(size: 56))
                .foregroundStyle(LinearGradient.magnetarGradient.opacity(0.7))
                .symbolRenderingMode(.hierarchical)

            // Text content
            VStack(spacing: 8) {
                Text(title)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.textPrimary)

                if let message = message {
                    Text(message)
                        .font(.system(size: 14))
                        .foregroundColor(.textSecondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 40)
                }
            }

            // Optional action button
            if let action = action, let actionLabel = actionLabel {
                Button(action: action) {
                    Text(actionLabel)
                        .font(.system(size: 14, weight: .medium))
                        .padding(.horizontal, 20)
                        .padding(.vertical, 10)
                        .background(Color.magnetarPrimary.opacity(0.1))
                        .foregroundColor(.magnetarPrimary)
                        .cornerRadius(8)
                }
                .buttonStyle(.plain)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}

// MARK: - Preview

#Preview("Basic Empty State") {
    EmptyState(
        icon: "folder",
        title: "No files yet",
        message: "Start by uploading your first file"
    )
    .frame(width: 400, height: 300)
}

#Preview("With Action") {
    EmptyState(
        icon: "plus.circle",
        title: "No items",
        message: "Get started by creating your first item",
        action: { print("Action tapped") },
        actionLabel: "Create Item"
    )
    .frame(width: 400, height: 300)
}
