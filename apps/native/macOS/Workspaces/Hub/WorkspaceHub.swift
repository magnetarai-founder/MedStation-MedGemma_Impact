//
//  WorkspaceHub.swift
//  MedStation
//
//  Main container — directly shows MedicalPanel.
//

import SwiftUI

struct WorkspaceHub: View {
    var body: some View {
        MedicalPanel()
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
