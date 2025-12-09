//
//  VaultAuditLogTab.swift
//  MagnetarStudio (macOS)
//
//  Audit log tab - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Displays file access audit history
//

import SwiftUI

struct VaultAuditLogTab: View {
    @ObservedObject var permissionManager: VaultPermissionManager

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if permissionManager.auditLog.isEmpty {
                VaultAdminEmptyState(
                    icon: "doc.text.fill",
                    title: "No Audit Entries",
                    message: "File access audit log is empty"
                )
            } else {
                ForEach(permissionManager.auditLog) { entry in
                    AuditEntryRow(entry: entry)
                }
            }
        }
    }
}
