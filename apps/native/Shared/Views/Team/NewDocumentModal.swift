//
//  NewDocumentModal.swift
//  MagnetarStudio
//
//  Modal for creating new documents with tile-based type selector
//

import SwiftUI

struct NewDocumentModal: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var isPresented: Bool

    @State private var selectedType: NewDocumentType? = nil
    @State private var title: String = ""
    @State private var isCreating: Bool = false
    @State private var errorMessage: String? = nil

    let onCreate: (String, NewDocumentType) async throws -> Void

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
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 40))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        Text("Create New Document")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text("Choose a document type to get started")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    // Document type tiles (4 options)
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 16) {
                        ForEach(NewDocumentType.allCases) { type in
                            documentTypeTile(type)
                        }
                    }

                    // Title input (only show if type selected)
                    if selectedType != nil {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Document Title")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)

                            TextField("Enter title...", text: $title)
                                .textFieldStyle(.roundedBorder)
                                .frame(height: 40)
                        }
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                    }

                    // Error message
                    if let error = errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }

                    // Action buttons
                    HStack(spacing: 12) {
                        GlassButton("Cancel", icon: "xmark", style: .secondary) {
                            dismiss()
                        }
                        .disabled(isCreating)

                        Spacer()

                        GlassButton(
                            isCreating ? "Creating..." : "Create",
                            icon: "checkmark",
                            style: .primary
                        ) {
                            Task {
                                await handleCreate()
                            }
                        }
                        .disabled(selectedType == nil || title.isEmpty || isCreating)
                    }
                }
                .padding(32)
            }
            .frame(width: 560, height: 520)
        }
    }

    // MARK: - Document Type Tile

    private func documentTypeTile(_ type: NewDocumentType) -> some View {
        Button {
            withAnimation(.spring(response: 0.3)) {
                selectedType = type
            }
        } label: {
            VStack(spacing: 12) {
                // Icon
                Image(systemName: type.icon)
                    .font(.system(size: 32))
                    .foregroundStyle(
                        selectedType == type
                            ? LinearGradient.magnetarGradient
                            : LinearGradient(colors: [.gray], startPoint: .top, endPoint: .bottom)
                    )

                // Name
                Text(type.displayName)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(selectedType == type ? .primary : .secondary)

                // Description
                Text(type.description)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
            .padding(.horizontal, 16)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(selectedType == type ? Color.blue.opacity(0.1) : Color.gray.opacity(0.05))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .strokeBorder(
                        selectedType == type
                            ? LinearGradient.magnetarGradient
                            : LinearGradient(colors: [.clear], startPoint: .top, endPoint: .bottom),
                        lineWidth: 2
                    )
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Create Handler

    private func handleCreate() async {
        guard let type = selectedType, !title.isEmpty else { return }

        isCreating = true
        errorMessage = nil

        do {
            try await onCreate(title, type)
            dismiss()
        } catch {
            errorMessage = "Failed to create document: \(error.localizedDescription)"
        }

        isCreating = false
    }
}

// MARK: - Document Type Enum

enum NewDocumentType: String, CaseIterable, Identifiable {
    case document
    case spreadsheet
    case insight
    case secureDocument

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .document: return "Document"
        case .spreadsheet: return "Spreadsheet"
        case .insight: return "Insight"
        case .secureDocument: return "Secure Doc"
        }
    }

    var icon: String {
        switch self {
        case .document: return "doc.text"
        case .spreadsheet: return "tablecells"
        case .insight: return "chart.line.uptrend.xyaxis"
        case .secureDocument: return "lock.doc"
        }
    }

    var description: String {
        switch self {
        case .document: return "Rich text notes"
        case .spreadsheet: return "Tables & data"
        case .insight: return "Analytics lab"
        case .secureDocument: return "Encrypted vault"
        }
    }

    var backendType: String {
        switch self {
        case .document: return "doc"
        case .spreadsheet: return "sheet"
        case .insight: return "insight"
        case .secureDocument: return "secure_doc"
        }
    }
}

// MARK: - Preview

#Preview {
    @Previewable @State var isPresented = true
    NewDocumentModal(isPresented: $isPresented) { title, type in
        print("Create: \(title) - \(type.displayName)")
    }
}
