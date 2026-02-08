//
//  VaultAdminHeader.swift
//  MagnetarStudio (macOS)
//
//  Vault admin panel header - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Displays active permission count and emergency revoke button
//

import SwiftUI

struct VaultAdminHeader: View {
    var permissionManager: VaultPermissionManager
    @Binding var showRevokeAllConfirmation: Bool

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: "lock.shield.fill")
                .font(.system(size: 28))
                .foregroundStyle(LinearGradient.magnetarGradient)

            VStack(alignment: .leading, spacing: 4) {
                Text("Vault Security Admin")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("\(permissionManager.activePermissions.count) active permissions • \(permissionManager.auditLog.count) audit entries")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // Emergency revoke all button
            Button {
                showRevokeAllConfirmation = true
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "exclamationmark.triangle.fill")
                    Text("Revoke All")
                }
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.red)
                .cornerRadius(6)
            }
            .buttonStyle(.plain)
            .help("Emergency: Revoke all file permissions immediately")
        }
        .padding(20)
    }
}
