//
//  SettingsHelpers.swift
//  MedStation
//
//  Shared helpers for settings views.
//

import SwiftUI

// MARK: - Helpers

enum SimpleStatus: Equatable {
    case idle
    case loading
    case success(String)
    case failure(String)

    var isSuccess: Bool {
        if case .success = self {
            return true
        }
        return false
    }
}

@ViewBuilder
func statusLabel(_ status: SimpleStatus) -> some View {
    switch status {
    case .idle:
        EmptyView()
    case .loading:
        HStack(spacing: 6) {
            ProgressView()
                .controlSize(.small)
            Text("Working...")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    case .success(let message):
        HStack(spacing: 6) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    case .failure(let message):
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}
