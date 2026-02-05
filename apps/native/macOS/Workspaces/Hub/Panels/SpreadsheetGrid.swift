//
//  SpreadsheetGrid.swift
//  MagnetarStudio
//
//  Grid view for spreadsheet cells with column/row headers,
//  cell selection, and inline editing.
//

import SwiftUI

struct SpreadsheetGrid: View {
    @Binding var document: SpreadsheetDocument
    @Binding var selectedCell: CellAddress?
    @Binding var editingCell: CellAddress?
    @State private var editText = ""

    private let defaultColumnWidth: CGFloat = 100
    private let rowHeaderWidth: CGFloat = 44
    private let headerHeight: CGFloat = 28
    private let cellHeight: CGFloat = 28

    var body: some View {
        ScrollView([.horizontal, .vertical]) {
            VStack(spacing: 0) {
                // Column headers
                columnHeaders

                // Rows
                LazyVStack(spacing: 0) {
                    ForEach(0..<document.rowCount, id: \.self) { row in
                        rowView(row: row)
                    }
                }
            }
        }
        .background(Color.surfacePrimary)
    }

    // MARK: - Column Headers

    private var columnHeaders: some View {
        HStack(spacing: 0) {
            // Top-left corner
            Rectangle()
                .fill(Color.surfaceTertiary)
                .frame(width: rowHeaderWidth, height: headerHeight)
                .overlay(alignment: .bottomTrailing) {
                    Rectangle().fill(Color.gray.opacity(0.2)).frame(height: 1)
                }

            // Column letters
            ForEach(0..<min(document.columnCount, 26), id: \.self) { col in
                Text(CellAddress.columnLetter(col))
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.secondary)
                    .frame(
                        width: CGFloat(document.columnWidth(for: col)),
                        height: headerHeight
                    )
                    .background(Color.surfaceTertiary)
                    .overlay(alignment: .trailing) {
                        Rectangle().fill(Color.gray.opacity(0.15)).frame(width: 1)
                    }
                    .overlay(alignment: .bottom) {
                        Rectangle().fill(Color.gray.opacity(0.2)).frame(height: 1)
                    }
            }
        }
    }

    // MARK: - Row View

    private func rowView(row: Int) -> some View {
        HStack(spacing: 0) {
            // Row number
            Text("\(row + 1)")
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
                .frame(width: rowHeaderWidth, height: cellHeight)
                .background(Color.surfaceTertiary)
                .overlay(alignment: .trailing) {
                    Rectangle().fill(Color.gray.opacity(0.15)).frame(width: 1)
                }
                .overlay(alignment: .bottom) {
                    Rectangle().fill(Color.gray.opacity(0.1)).frame(height: 1)
                }

            // Cells
            ForEach(0..<min(document.columnCount, 26), id: \.self) { col in
                let addr = CellAddress(column: col, row: row)
                cellView(at: addr)
            }
        }
    }

    // MARK: - Cell View

    private func cellView(at address: CellAddress) -> some View {
        let cell = document.cell(at: address)
        let isSelected = selectedCell == address
        let isEditing = editingCell == address

        return ZStack {
            // Background
            Rectangle()
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.08) : Color.clear)

            if isEditing {
                // Edit mode
                TextField("", text: $editText, onCommit: {
                    commitEdit(at: address)
                })
                .textFieldStyle(.plain)
                .font(.system(size: 12, weight: cell.isBold ? .semibold : .regular))
                .padding(.horizontal, 4)
            } else {
                // Display mode
                let displayValue = cell.isFormula
                    ? FormulaEngine(cells: document.cells).evaluate(cell.rawValue)
                    : cell.rawValue

                Text(displayValue)
                    .font(.system(size: 12, weight: cell.isBold ? .semibold : .regular))
                    .italic(cell.isItalic)
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: alignment(for: cell))
                    .padding(.horizontal, 4)
            }
        }
        .frame(
            width: CGFloat(document.columnWidth(for: address.column)),
            height: cellHeight
        )
        .overlay(alignment: .trailing) {
            Rectangle().fill(Color.gray.opacity(0.1)).frame(width: 1)
        }
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color.gray.opacity(0.1)).frame(height: 1)
        }
        .overlay {
            if isSelected {
                Rectangle()
                    .stroke(Color.magnetarPrimary, lineWidth: 2)
            }
        }
        .contentShape(Rectangle())
        .onTapGesture {
            if selectedCell == address {
                // Double-tap enters edit mode
                startEditing(at: address)
            } else {
                selectedCell = address
                editingCell = nil
            }
        }
        .simultaneousGesture(
            TapGesture(count: 2).onEnded {
                startEditing(at: address)
            }
        )
    }

    // MARK: - Editing

    private func startEditing(at address: CellAddress) {
        let cell = document.cell(at: address)
        editText = cell.rawValue
        selectedCell = address
        editingCell = address
    }

    private func commitEdit(at address: CellAddress) {
        document.setCell(at: address, value: editText)
        editingCell = nil
    }

    private func alignment(for cell: SpreadsheetCell) -> Alignment {
        switch cell.alignment {
        case .left: return .leading
        case .center: return .center
        case .right: return .trailing
        }
    }
}
