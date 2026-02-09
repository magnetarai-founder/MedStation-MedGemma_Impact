//
//  SheetsToolbar.swift
//  MagnetarStudio
//
//  Toolbar for the spreadsheet panel — cell address, formula bar, AI, chart.
//

import SwiftUI

struct SheetsToolbar: View {
    @Binding var document: SpreadsheetDocument
    @Binding var selectedCell: CellAddress?
    @Binding var formulaText: String
    let onFormulaCommit: () -> Void
    @State private var showFormulaAI = false
    @State private var showChartBuilder = false

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

            // AI formula assistant
            Button {
                showFormulaAI.toggle()
            } label: {
                Image(systemName: "sparkles")
                    .font(.system(size: 12))
                    .foregroundStyle(.purple)
                    .frame(width: 24, height: 24)
            }
            .buttonStyle(.plain)
            .help("Formula AI")
            .accessibilityLabel("Formula AI")
            .popover(isPresented: $showFormulaAI) {
                FormulaAIPopover(
                    selectedCell: selectedCell,
                    onInsertFormula: { formula in
                        formulaText = formula
                        onFormulaCommit()
                        showFormulaAI = false
                    },
                    onDismiss: {
                        showFormulaAI = false
                    }
                )
            }

            // Chart button
            Button {
                showChartBuilder.toggle()
            } label: {
                Image(systemName: "chart.bar.xaxis")
                    .font(.system(size: 12))
                    .foregroundStyle(.orange)
                    .frame(width: 24, height: 24)
            }
            .buttonStyle(.plain)
            .help("Insert Chart")
            .accessibilityLabel("Insert Chart")
            .sheet(isPresented: $showChartBuilder) {
                SheetsChartSheet(
                    document: document,
                    onInsert: { _ in
                        showChartBuilder = false
                    },
                    onDismiss: { showChartBuilder = false }
                )
            }

            Spacer()
        }
        .padding(.horizontal, 12)
        .frame(height: HubLayout.headerHeight)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

}
