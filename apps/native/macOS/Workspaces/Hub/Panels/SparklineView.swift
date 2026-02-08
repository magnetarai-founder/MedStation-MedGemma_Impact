//
//  SparklineView.swift
//  MagnetarStudio (macOS)
//
//  Tiny inline chart for spreadsheet cells — rendered by SpreadsheetGrid for =SPARKLINE() formulas.
//  Renders as a mini line or bar sparkline within cell bounds.
//

import SwiftUI
import Charts

struct SparklineView: View {
    let values: [Double]
    var style: SparklineStyle = .line
    var color: Color = .blue

    enum SparklineStyle {
        case line
        case bar
    }

    var body: some View {
        switch style {
        case .line:
            lineSparkline
        case .bar:
            barSparkline
        }
    }

    private var lineSparkline: some View {
        Chart(Array(values.enumerated()), id: \.offset) { index, value in
            LineMark(
                x: .value("Index", index),
                y: .value("Value", value)
            )
            .foregroundStyle(color)
            .interpolationMethod(.catmullRom)
        }
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
        .chartLegend(.hidden)
    }

    private var barSparkline: some View {
        Chart(Array(values.enumerated()), id: \.offset) { index, value in
            BarMark(
                x: .value("Index", index),
                y: .value("Value", value)
            )
            .foregroundStyle(color.opacity(0.7))
        }
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
        .chartLegend(.hidden)
    }
}

/// Parse sparkline cell formula: =SPARKLINE(A1:A10, "line")
struct SparklineParser {
    static func parse(formula: String, cells: [String: SpreadsheetCell]) -> (values: [Double], style: SparklineView.SparklineStyle)? {
        let upper = formula.uppercased()
        guard upper.hasPrefix("=SPARKLINE(") else { return nil }

        let inner = String(formula.dropFirst(11).dropLast())
        let parts = inner.split(separator: ",", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }

        guard let rangePart = parts.first else { return nil }

        // Parse style
        var style: SparklineView.SparklineStyle = .line
        if parts.count > 1 {
            let stylePart = parts[1].trimmingCharacters(in: CharacterSet(charactersIn: "\"' ")).lowercased()
            if stylePart == "bar" { style = .bar }
        }

        // Resolve range to values
        let engine = FormulaEngine(cells: cells)
        let rangeParts = rangePart.split(separator: ":")
        guard rangeParts.count == 2,
              let start = CellAddress.fromString(String(rangeParts[0])),
              let end = CellAddress.fromString(String(rangeParts[1])) else {
            return nil
        }

        var values: [Double] = []
        if start.column == end.column {
            // Vertical range
            for row in start.row...end.row {
                let addr = CellAddress(column: start.column, row: row)
                let cell = cells[addr.description]
                let raw = cell?.rawValue ?? ""
                let evaluated = engine.evaluate(raw)
                if let val = Double(evaluated) {
                    values.append(val)
                }
            }
        } else if start.row == end.row {
            // Horizontal range
            for col in start.column...end.column {
                let addr = CellAddress(column: col, row: start.row)
                let cell = cells[addr.description]
                let raw = cell?.rawValue ?? ""
                let evaluated = engine.evaluate(raw)
                if let val = Double(evaluated) {
                    values.append(val)
                }
            }
        }

        guard !values.isEmpty else { return nil }
        return (values, style)
    }
}
