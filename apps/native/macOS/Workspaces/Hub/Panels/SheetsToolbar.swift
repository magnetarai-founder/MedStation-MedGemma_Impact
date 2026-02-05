//
//  SheetsToolbar.swift
//  MagnetarStudio
//
//  Toolbar for the spreadsheet panel — formula bar, formatting controls.
//

import SwiftUI

struct SheetsToolbar: View {
    @Binding var document: SpreadsheetDocument
    @Binding var selectedCell: CellAddress?
    @Binding var formulaText: String
    let onFormulaCommit: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            // Cell address display
            Text(selectedCell?.description ?? "—")
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundStyle(.primary)
                .frame(width: 50)
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .background(Color.surfaceTertiary)
                .clipShape(RoundedRectangle(cornerRadius: 4))

            // Formula bar
            HStack(spacing: 4) {
                Text("fx")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(.secondary)

                TextField("", text: $formulaText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12, design: .monospaced))
                    .onSubmit { onFormulaCommit() }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.surfaceTertiary)
            .clipShape(RoundedRectangle(cornerRadius: 4))

            Spacer()

            // Formatting buttons
            Group {
                formatButton(icon: "bold", help: "Bold")
                formatButton(icon: "italic", help: "Italic")
            }

            Divider().frame(height: 16)

            // Alignment
            Group {
                formatButton(icon: "text.alignleft", help: "Align Left")
                formatButton(icon: "text.aligncenter", help: "Center")
                formatButton(icon: "text.alignright", help: "Align Right")
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

    private func formatButton(icon: String, help: String) -> some View {
        Button {} label: {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .frame(width: 24, height: 24)
        }
        .buttonStyle(.plain)
        .help(help)
    }
}
