//
//  ChartConfiguration.swift
//  MagnetarStudio
//
//  Chart model — type, configuration, data series, color schemes.
//  Codable for persistence in WorkspaceEditor chart blocks.
//

import Foundation
import SwiftUI

// MARK: - Chart Type

enum ChartType: String, CaseIterable, Identifiable, Codable, Sendable {
    case bar = "Bar"
    case line = "Line"
    case pie = "Pie"
    case scatter = "Scatter"
    case area = "Area"
    case donut = "Donut"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .bar: return "chart.bar"
        case .line: return "chart.line.uptrend.xyaxis"
        case .pie: return "chart.pie"
        case .scatter: return "chart.dots.scatter"
        case .area: return "chart.line.uptrend.xyaxis"
        case .donut: return "chart.pie"
        }
    }
}

// MARK: - Data Point

struct ChartDataPoint: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var label: String
    var value: Double
    var secondaryValue: Double?  // For scatter (x,y)

    init(id: UUID = UUID(), label: String, value: Double, secondaryValue: Double? = nil) {
        self.id = id
        self.label = label
        self.value = value
        self.secondaryValue = secondaryValue
    }
}

// MARK: - Data Series

struct ChartDataSeries: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var label: String
    var points: [ChartDataPoint]
    var colorHex: String

    init(id: UUID = UUID(), label: String, points: [ChartDataPoint] = [], colorHex: String = "#007AFF") {
        self.id = id
        self.label = label
        self.points = points
        self.colorHex = colorHex
    }

    var color: Color {
        Color(hex: colorHex) ?? .blue
    }
}

// MARK: - Color Scheme

enum ChartColorScheme: String, CaseIterable, Identifiable, Codable, Sendable {
    case `default` = "Default"
    case ocean = "Ocean"
    case sunset = "Sunset"
    case forest = "Forest"
    case monochrome = "Monochrome"
    case pastel = "Pastel"

    var id: String { rawValue }

    var colors: [Color] {
        switch self {
        case .default:
            return [.blue, .green, .orange, .red, .purple, .cyan]
        case .ocean:
            return [
                Color(red: 0.0, green: 0.47, blue: 0.84),
                Color(red: 0.0, green: 0.65, blue: 0.78),
                Color(red: 0.27, green: 0.75, blue: 0.72),
                Color(red: 0.56, green: 0.84, blue: 0.66),
                Color(red: 0.78, green: 0.92, blue: 0.67),
                Color(red: 0.15, green: 0.35, blue: 0.6)
            ]
        case .sunset:
            return [
                Color(red: 0.95, green: 0.27, blue: 0.27),
                Color(red: 0.97, green: 0.52, blue: 0.25),
                Color(red: 0.98, green: 0.75, blue: 0.25),
                Color(red: 0.96, green: 0.35, blue: 0.55),
                Color(red: 0.85, green: 0.2, blue: 0.5),
                Color(red: 0.6, green: 0.15, blue: 0.45)
            ]
        case .forest:
            return [
                Color(red: 0.13, green: 0.55, blue: 0.13),
                Color(red: 0.2, green: 0.7, blue: 0.35),
                Color(red: 0.56, green: 0.74, blue: 0.22),
                Color(red: 0.33, green: 0.42, blue: 0.18),
                Color(red: 0.0, green: 0.5, blue: 0.0),
                Color(red: 0.47, green: 0.62, blue: 0.15)
            ]
        case .monochrome:
            return [
                Color(white: 0.1),
                Color(white: 0.25),
                Color(white: 0.4),
                Color(white: 0.55),
                Color(white: 0.7),
                Color(white: 0.85)
            ]
        case .pastel:
            return [
                Color(red: 0.68, green: 0.85, blue: 0.9),
                Color(red: 1.0, green: 0.71, blue: 0.76),
                Color(red: 0.78, green: 0.96, blue: 0.71),
                Color(red: 1.0, green: 0.92, blue: 0.63),
                Color(red: 0.8, green: 0.72, blue: 0.96),
                Color(red: 1.0, green: 0.85, blue: 0.68)
            ]
        }
    }

    func color(at index: Int) -> Color {
        colors[index % colors.count]
    }
}

// MARK: - Chart Configuration

struct ChartConfiguration: Codable, Equatable, Sendable {
    var type: ChartType
    var title: String
    var xAxisLabel: String
    var yAxisLabel: String
    var showLegend: Bool
    var showGrid: Bool
    var colorScheme: ChartColorScheme
    var series: [ChartDataSeries]

    // Source data range (for spreadsheet-linked charts)
    var sourceRange: String?  // "A1:D10"

    init(
        type: ChartType = .bar,
        title: String = "Chart",
        xAxisLabel: String = "",
        yAxisLabel: String = "",
        showLegend: Bool = true,
        showGrid: Bool = true,
        colorScheme: ChartColorScheme = .default,
        series: [ChartDataSeries] = [],
        sourceRange: String? = nil
    ) {
        self.type = type
        self.title = title
        self.xAxisLabel = xAxisLabel
        self.yAxisLabel = yAxisLabel
        self.showLegend = showLegend
        self.showGrid = showGrid
        self.colorScheme = colorScheme
        self.series = series
        self.sourceRange = sourceRange
    }
}

// MARK: - Color Extension

extension Color {
    init?(hex: String) {
        var hex = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        hex = hex.replacingOccurrences(of: "#", with: "")

        guard hex.count == 6,
              let rgb = UInt64(hex, radix: 16) else { return nil }

        self.init(
            red: Double((rgb >> 16) & 0xFF) / 255.0,
            green: Double((rgb >> 8) & 0xFF) / 255.0,
            blue: Double(rgb & 0xFF) / 255.0
        )
    }
}
