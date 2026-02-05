//
//  VaultAdminPanel.swift
//  MagnetarStudio (macOS)
//
//  STUB: Not currently wired — future vault administration panel (between Control Center and Panic in header).
//  Vault security admin panel for monitoring and emergency revocation
//  Refactored in Phase 6.16 - extracted tabs and components
//
//  Part of Noah's Ark for the Digital Age - Protecting God's people
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI

struct VaultAdminPanel: View {
    @State private var permissionManager = VaultPermissionManager.shared
    @State private var hotSlotManager = HotSlotManager.shared

    @State private var selectedTab: AdminTab = .permissions
    @State private var showRevokeAllConfirmation: Bool = false

    enum AdminTab: String, CaseIterable {
        case permissions = "Active Permissions"
        case audit = "Audit Log"
        case resources = "Resource Usage"
        case security = "Security Audit"
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VaultAdminHeader(
                permissionManager: permissionManager,
                showRevokeAllConfirmation: $showRevokeAllConfirmation
            )

            Divider()

            // Tab selector
            HStack(spacing: 0) {
                ForEach(AdminTab.allCases, id: \.self) { tab in
                    Button {
                        selectedTab = tab
                    } label: {
                        Text(tab.rawValue)
                            .font(.system(size: 13, weight: selectedTab == tab ? .semibold : .regular))
                            .foregroundColor(selectedTab == tab ? .magnetarPrimary : .secondary)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                            .background(
                                selectedTab == tab ?
                                Color.magnetarPrimary.opacity(0.1) : Color.clear
                            )
                            .cornerRadius(6)
                    }
                    .buttonStyle(.plain)
                }

                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 8)
            .background(Color.surfaceSecondary.opacity(0.2))

            Divider()

            // Tab content
            ScrollView {
                Group {
                    switch selectedTab {
                    case .permissions:
                        VaultPermissionsTab(permissionManager: permissionManager)
                    case .audit:
                        VaultAuditLogTab(permissionManager: permissionManager)
                    case .resources:
                        VaultResourcesTab(hotSlotManager: hotSlotManager)
                    case .security:
                        VaultSecurityAuditTab(permissionManager: permissionManager)
                    }
                }
                .padding(20)
            }
        }
        .frame(width: 800, height: 600)
        .alert("Revoke All Permissions?", isPresented: $showRevokeAllConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Revoke All", role: .destructive) {
                permissionManager.revokeAllPermissions()
            }
        } message: {
            Text("This will immediately revoke ALL file permissions for ALL models. This action cannot be undone.")
        }
    }
}

// MARK: - Preview

#Preview {
    VaultAdminPanel()
}
