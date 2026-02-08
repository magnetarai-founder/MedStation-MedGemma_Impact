//
//  WorkflowDesignerView.swift
//  MagnetarStudio
//
//  Workflow designer view placeholder
//

import SwiftUI

struct WorkflowDesignerView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "paintbrush")
                .font(.system(size: 64))
                .foregroundStyle(.secondary)

            Text("Workflow Designer")
                .font(.title)

            Text("Stage list and editor will appear here")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}
