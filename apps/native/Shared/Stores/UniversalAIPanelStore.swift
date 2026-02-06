//
//  UniversalAIPanelStore.swift
//  MagnetarStudio
//
//  State management for the universal AI side panel.
//  Controls visibility and width across all workspaces.
//

import Foundation
import Observation
import SwiftUI

@MainActor
@Observable
final class UniversalAIPanelStore {
    static let shared = UniversalAIPanelStore()

    var isVisible: Bool {
        didSet { UserDefaults.standard.set(isVisible, forKey: "universalAI.isVisible") }
    }

    @ObservationIgnored
    @AppStorage("universalAI.panelWidth") var panelWidth: Double = 320

    static let minWidth: CGFloat = 260
    static let maxWidth: CGFloat = 500

    private init() {
        self.isVisible = UserDefaults.standard.bool(forKey: "universalAI.isVisible")
    }

    func toggle() {
        withAnimation(.magnetarQuick) {
            isVisible.toggle()
        }
    }
}
