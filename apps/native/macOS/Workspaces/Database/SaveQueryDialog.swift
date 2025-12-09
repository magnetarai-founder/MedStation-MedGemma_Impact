//
//  SaveQueryDialog.swift
//  MagnetarStudio (macOS)
//
//  Save query form dialog - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI

struct SaveQueryDialog: View {
    @Binding var isPresented: Bool
    let queryText: String
    @ObservedObject var databaseStore: DatabaseStore

    @State private var queryName: String = ""
    @State private var queryDescription: String = ""
    @State private var isSaving: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        VStack(spacing: 20) {
            Text("Save Query")
                .font(.title2)
                .fontWeight(.semibold)

            VStack(alignment: .leading, spacing: 8) {
                Text("Name")
                    .font(.system(size: 13, weight: .medium))
                TextField("Query name", text: $queryName)
                    .textFieldStyle(.roundedBorder)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Description (optional)")
                    .font(.system(size: 13, weight: .medium))
                TextField("Description", text: $queryDescription)
                    .textFieldStyle(.roundedBorder)
            }

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }

            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .buttonStyle(.bordered)

                Button(isSaving ? "Saving..." : "Save") {
                    Task { await saveQuery() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(queryName.isEmpty || isSaving)
            }
        }
        .padding(24)
        .frame(width: 400)
    }

    @MainActor
    private func saveQuery() async {
        isSaving = true
        errorMessage = nil

        do {
            var jsonBody: [String: Any] = [
                "name": queryName,
                "query": queryText,
                "query_type": "sql"
            ]
            if !queryDescription.isEmpty {
                jsonBody["description"] = queryDescription
            }

            let _: SaveQueryResponse = try await ApiClient.shared.request(
                path: "/saved-queries",
                method: .post,
                jsonBody: jsonBody
            )

            isSaving = false
            isPresented = false
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}
