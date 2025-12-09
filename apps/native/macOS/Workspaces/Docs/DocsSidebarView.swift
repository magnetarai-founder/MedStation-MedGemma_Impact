//
//  DocsSidebarView.swift
//  MagnetarStudio (macOS)
//
//  Documents sidebar view - Extracted from DocsWorkspaceView.swift (Phase 6.21)
//

import SwiftUI

struct DocsSidebarView: View {
    let documents: [TeamDocument]
    let activeDocument: TeamDocument?
    let onSelectDocument: (TeamDocument) -> Void
    let onNewDocument: () -> Void
    let onEditDocument: (TeamDocument) -> Void
    let onDeleteDocument: (TeamDocument) async -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Sidebar header
            HStack(spacing: 12) {
                Image(systemName: "doc.text.fill")
                    .font(.system(size: 18))
                    .foregroundColor(Color.magnetarPrimary)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Documents")
                        .font(.system(size: 16, weight: .semibold))

                    Text("\(documents.count) document\(documents.count == 1 ? "" : "s")")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button(action: onNewDocument) {
                    Image(systemName: "plus")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    // Documents section header
                    HStack {
                        Text("DOCUMENTS")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.secondary)
                            .textCase(.uppercase)

                        Spacer()
                    }
                    .padding(.bottom, 4)

                    // Document list
                    ForEach(documents) { doc in
                        DocumentRowView(
                            doc: doc,
                            isActive: activeDocument?.id == doc.id,
                            onSelect: { onSelectDocument(doc) },
                            onEdit: { onEditDocument(doc) },
                            onDelete: {
                                Task {
                                    await onDeleteDocument(doc)
                                }
                            }
                        )
                    }
                }
                .padding(.horizontal, 8)
                .padding(.top, 16)
                .padding(.bottom, 8)
            }
        }
        .frame(width: 256)
    }
}
