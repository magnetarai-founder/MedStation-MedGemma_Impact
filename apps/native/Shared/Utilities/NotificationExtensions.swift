//
//  NotificationExtensions.swift
//  MagnetarStudio
//
//  Shared notification name extensions used across components
//

import Foundation

extension Notification.Name {
    /// Posted to clear the current workspace state (e.g., database results, file uploads)
    static let clearWorkspace = Notification.Name("DatabaseWorkspaceClearWorkspace")
}
