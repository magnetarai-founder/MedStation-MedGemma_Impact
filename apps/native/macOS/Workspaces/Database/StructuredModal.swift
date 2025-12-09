//
//  StructuredModal.swift
//  MagnetarStudio (macOS)
//
//  Base modal container component - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI

struct StructuredModal<Content: View>: View {
    let title: String
    @Binding var isPresented: Bool
    @ViewBuilder let content: Content

    var body: some View {
        VStack(spacing: 0) {
            // Header with title + close X
            HStack {
                Text(title)
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color(nsColor: .controlBackgroundColor))
                        )
                }
                .buttonStyle(.plain)
                .help("Close (Esc)")
                .keyboardShortcut(.cancelAction)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)

            Divider()

            // Content
            content
        }
        .frame(width: 700, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .cornerRadius(12)
        .shadow(radius: 20)
    }
}
