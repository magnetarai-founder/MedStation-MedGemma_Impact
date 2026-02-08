//
//  EditQueryDialog.swift
//  MagnetarStudio (macOS)
//
//  Edit query form dialog - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI

struct EditQueryDialog: View {
    @Binding var isPresented: Bool
    let query: SavedQuery
    let onUpdate: (String, String, String) -> Void  // name, description, sql

    @State private var editedName: String = ""
    @State private var editedDescription: String = ""
    @State private var editedSQL: String = ""

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Text("Edit Query")
                    .font(.title2)
                    .fontWeight(.semibold)
                Spacer()
                Button(action: { isPresented = false }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Name field
            VStack(alignment: .leading, spacing: 8) {
                Text("Name")
                    .font(.system(size: 13, weight: .medium))
                TextField("Query name", text: $editedName)
                    .textFieldStyle(.roundedBorder)
            }

            // Description field
            VStack(alignment: .leading, spacing: 8) {
                Text("Description (optional)")
                    .font(.system(size: 13, weight: .medium))
                TextField("Description", text: $editedDescription)
                    .textFieldStyle(.roundedBorder)
            }

            // SQL Editor
            VStack(alignment: .leading, spacing: 8) {
                Text("SQL Query")
                    .font(.system(size: 13, weight: .medium))

                TextEditor(text: $editedSQL)
                    .font(.system(size: 13, design: .monospaced))
                    .frame(height: 300)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
            }

            // Action buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .buttonStyle(.bordered)

                Button("Save Changes") {
                    onUpdate(editedName, editedDescription, editedSQL)
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .disabled(editedName.isEmpty || editedSQL.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 600)
        .onAppear {
            editedName = query.name
            editedDescription = query.description ?? ""
            editedSQL = query.query
        }
    }
}
