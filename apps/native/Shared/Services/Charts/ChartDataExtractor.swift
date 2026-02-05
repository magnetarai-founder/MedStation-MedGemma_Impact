//
//  ChartDataExtractor.swift
//  MagnetarStudio
//
//  Extracts chart data from SpreadsheetDocument given column/row ranges.
//  Evaluates formulas via FormulaEngine before extracting numeric values.
//

import Foundation
import SwiftUI
import AppKit

struct ChartDataExtractor {

    // MARK: - Public API

    /// Extract chart data series from a spreadsheet using a range string like "A1:D10".
    /// First column/row used as labels, remaining columns become separate series.
    static func extract(
        from document: SpreadsheetDocument,
        range: String,
        orientation: DataOrientation = .columnsAsSeries
    ) -> [ChartDataSeries] {
        guard let (start, end) = parseRange(range) else { return [] }

        let engine = FormulaEngine(cells: document.cells)

        switch orientation {
        case .columnsAsSeries:
            return extractColumnSeries(document: document, engine: engine, start: start, end: end)
        case .rowsAsSeries:
            return extractRowSeries(document: document, engine: engine, start: start, end: end)
        }
    }

    /// Auto-detect data from the entire populated region of a spreadsheet.
    static func autoExtract(from document: SpreadsheetDocument) -> [ChartDataSeries] {
        let bounds = dataBounds(document)
        guard bounds.maxRow >= bounds.minRow, bounds.maxCol >= bounds.minCol else { return [] }

        let rangeStr = "\(CellAddress.columnLetter(bounds.minCol))\(bounds.minRow + 1):\(CellAddress.columnLetter(bounds.maxCol))\(bounds.maxRow + 1)"
        return extract(from: document, range: rangeStr)
    }

    /// Get cell value as a string, evaluating formulas.
    static func evaluatedValue(
        document: SpreadsheetDocument,
        engine: FormulaEngine,
        address: CellAddress
    ) -> String {
        let cell = document.cell(at: address)
        let raw = cell.rawValue
        guard !raw.isEmpty else { return "" }
        return engine.evaluate(raw)
    }

    // MARK: - Column-oriented Extraction

    /// First column = labels, remaining columns = one series each.
    /// First row in range = series labels (headers).
    private static func extractColumnSeries(
        document: SpreadsheetDocument,
        engine: FormulaEngine,
        start: CellAddress,
        end: CellAddress
    ) -> [ChartDataSeries] {
        let palette = ChartColorScheme.default

        // Row 0 of range = headers
        let headerRow = start.row
        let dataStartRow = start.row + 1
        let labelCol = start.column

        var seriesList: [ChartDataSeries] = []

        // Each column after the label column is a series
        for col in (start.column + 1)...end.column {
            let headerAddr = CellAddress(column: col, row: headerRow)
            let seriesLabel = evaluatedValue(document: document, engine: engine, address: headerAddr)

            var points: [ChartDataPoint] = []
            for row in dataStartRow...end.row {
                let labelAddr = CellAddress(column: labelCol, row: row)
                let valueAddr = CellAddress(column: col, row: row)

                let label = evaluatedValue(document: document, engine: engine, address: labelAddr)
                let valueStr = evaluatedValue(document: document, engine: engine, address: valueAddr)
                let value = Double(valueStr) ?? 0

                guard !label.isEmpty else { continue }
                points.append(ChartDataPoint(label: label, value: value))
            }

            let colorIndex = col - start.column - 1
            let color = palette.color(at: colorIndex)
            seriesList.append(ChartDataSeries(
                label: seriesLabel.isEmpty ? "Series \(colorIndex + 1)" : seriesLabel,
                points: points,
                colorHex: color.toHex() ?? "#007AFF"
            ))
        }

        return seriesList
    }

    // MARK: - Row-oriented Extraction

    /// First row = labels, remaining rows = one series each.
    /// First column in range = series labels (headers).
    private static func extractRowSeries(
        document: SpreadsheetDocument,
        engine: FormulaEngine,
        start: CellAddress,
        end: CellAddress
    ) -> [ChartDataSeries] {
        let palette = ChartColorScheme.default

        let headerCol = start.column
        let dataStartCol = start.column + 1
        let labelRow = start.row

        var seriesList: [ChartDataSeries] = []

        for row in (start.row + 1)...end.row {
            let headerAddr = CellAddress(column: headerCol, row: row)
            let seriesLabel = evaluatedValue(document: document, engine: engine, address: headerAddr)

            var points: [ChartDataPoint] = []
            for col in dataStartCol...end.column {
                let labelAddr = CellAddress(column: col, row: labelRow)
                let valueAddr = CellAddress(column: col, row: row)

                let label = evaluatedValue(document: document, engine: engine, address: labelAddr)
                let valueStr = evaluatedValue(document: document, engine: engine, address: valueAddr)
                let value = Double(valueStr) ?? 0

                guard !label.isEmpty else { continue }
                points.append(ChartDataPoint(label: label, value: value))
            }

            let colorIndex = row - start.row - 1
            let color = palette.color(at: colorIndex)
            seriesList.append(ChartDataSeries(
                label: seriesLabel.isEmpty ? "Series \(colorIndex + 1)" : seriesLabel,
                points: points,
                colorHex: color.toHex() ?? "#007AFF"
            ))
        }

        return seriesList
    }

    // MARK: - Range Parsing

    /// Parse "A1:D10" → (CellAddress, CellAddress)
    static func parseRange(_ range: String) -> (CellAddress, CellAddress)? {
        let parts = range.uppercased().split(separator: ":")
        guard parts.count == 2,
              let start = CellAddress.fromString(String(parts[0])),
              let end = CellAddress.fromString(String(parts[1])) else {
            return nil
        }
        // Normalize so start ≤ end
        let minCol = min(start.column, end.column)
        let maxCol = max(start.column, end.column)
        let minRow = min(start.row, end.row)
        let maxRow = max(start.row, end.row)
        return (CellAddress(column: minCol, row: minRow), CellAddress(column: maxCol, row: maxRow))
    }

    // MARK: - Data Bounds

    /// Find the bounding rectangle of populated cells.
    static func dataBounds(_ document: SpreadsheetDocument) -> (minRow: Int, maxRow: Int, minCol: Int, maxCol: Int) {
        var minRow = Int.max, maxRow = 0
        var minCol = Int.max, maxCol = 0

        for key in document.cells.keys {
            guard let addr = CellAddress.fromString(key) else { continue }
            let cell = document.cells[key]
            guard let cell = cell, !cell.rawValue.isEmpty else { continue }

            minRow = min(minRow, addr.row)
            maxRow = max(maxRow, addr.row)
            minCol = min(minCol, addr.column)
            maxCol = max(maxCol, addr.column)
        }

        if minRow > maxRow { return (0, 0, 0, 0) }
        return (minRow, maxRow, minCol, maxCol)
    }

    // MARK: - Types

    enum DataOrientation {
        case columnsAsSeries  // Default: each column is a series
        case rowsAsSeries     // Each row is a series
    }
}

// MARK: - Color to Hex

extension Color {
    func toHex() -> String? {
        guard let components = NSColor(self).usingColorSpace(.deviceRGB) else { return nil }
        let r = Int(components.redComponent * 255)
        let g = Int(components.greenComponent * 255)
        let b = Int(components.blueComponent * 255)
        return String(format: "#%02X%02X%02X", r, g, b)
    }
}
