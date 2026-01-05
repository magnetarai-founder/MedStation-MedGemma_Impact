//
//  NotificationExtensions.swift
//  MagnetarStudio
//
//  Shared notification name extensions used across components.
//  NOTE: Prefer direct store method calls over NotificationCenter for better type safety.
//

import Foundation

extension Notification.Name {
    // Deprecated: Use DatabaseStore.shared.clearWorkspace() instead (MEDIUM-H3)
    // Kept for backwards compatibility - can be removed in next major version
    @available(*, deprecated, message: "Use DatabaseStore.clearWorkspace() instead")
    static let clearWorkspace = Notification.Name("DatabaseWorkspaceClearWorkspace")
}
