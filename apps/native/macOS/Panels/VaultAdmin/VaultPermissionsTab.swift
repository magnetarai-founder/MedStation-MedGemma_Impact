//
//  VaultPermissionsTab.swift
//  MagnetarStudio (macOS)
//
//  Active permissions tab - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Displays and manages active file permissions
//

import SwiftUI

struct VaultPermissionsTab: View {
    @ObservedObject var permissionManager: VaultPermissionManager

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if permissionManager.activePermissions.isEmpty {
                VaultAdminEmptyState(
                    icon: "checkmark.shield.fill",
                    title: "No Active Permissions",
                    message: "No models currently have access to vault files"
                )
            } else {
                ForEach(permissionManager.activePermissions) { permission in
                    PermissionCard(
                        permission: permission,
                        onRevoke: {
                            permissionManager.revokePermission(permission)
                        }
                    )
                }
            }
        }
    }
}
