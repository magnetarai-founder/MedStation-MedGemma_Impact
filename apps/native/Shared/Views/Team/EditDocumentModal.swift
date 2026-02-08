//
//  EditDocumentModal.swift
//  MagnetarStudio
//
//  Modal for editing document title
//

import SwiftUI

struct EditDocumentModal: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var isPresented: Bool
    let document: TeamDocument

    @State private var title: String = ""
    @State private var isSaving: Bool = false
    @State private var errorMessage: String? = nil

    let onSave: (String) async throws -> Void

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient.magnetarGradient
                .opacity(0.3)
                .ignoresSafeArea()

            LiquidGlassPanel(material: .thick) {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "pencil.circle.fill")
                            .font(.system(size: 40))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("Edit Document")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text("Update the document title")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    // Title input
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Document Title")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.secondary)

                        TextField("Enter title...", text: $title)
                            .textFieldStyle(.roundedBorder)
                            .frame(height: 40)
                    }

                    // Error message
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }

                    // Action buttons
                    HStack(spacing: 12) {
                        GlassButton("Cancel", icon: "xmark", style: .secondary) {
                            dismiss()
                        }
                        .disabled(isSaving)

                        Spacer()

                        GlassButton(
                            isSaving ? "Saving..." : "Save",
                            icon: "checkmark",
                            style: .primary
                        ) {
                            Task {
                                await handleSave()
                            }
                        }
                        .disabled(title.isEmpty || isSaving)
                    }
                }
                .padding(32)
            }
            .frame(width: 400, height: 300)
        }
        .onAppear {
            title = document.title
        }
    }

    // MARK: - Save Handler

    private func handleSave() async {
        guard !title.isEmpty else { return }

        isSaving = true
        errorMessage = nil

        do {
            try await onSave(title)
            dismiss()
        } catch {
            errorMessage = "Failed to update document: \(error.localizedDescription)"
        }

        isSaving = false
    }
}
