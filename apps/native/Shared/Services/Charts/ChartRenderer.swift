//
//  ChartRenderer.swift
//  MagnetarStudio
//
//  Renders ChartConfiguration as SwiftUI Chart views.
//  Supports all 6 chart types using Swift Charts framework.
//  Also handles PNG export via ImageRenderer.
//

import SwiftUI
import Charts
import AppKit

// MARK: - Indexed Point (for pie/donut)

private struct IndexedPoint: Identifiable {
    let id: UUID
    let index: Int
    let label: String
    let value: Double
}

// MARK: - Chart Renderer View

struct ChartRendererView: View {
    let config: ChartConfiguration
    var height: CGFloat = 300

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !config.title.isEmpty {
                Text(config.title)
                    .font(.system(size: 14, weight: .semibold))
            }

            chartContent
                .frame(height: height)

            if config.showLegend && config.series.count > 1 {
                legendView
            }
        }
    }

    // MARK: - Chart Content

    @ViewBuilder
    private var chartContent: some View {
        switch config.type {
        case .bar:
            barChart
        case .line:
            lineChart
        case .area:
            areaChart
        case .scatter:
            scatterChart
        case .pie:
            sectorChart(innerRadius: 0)
        case .donut:
            sectorChart(innerRadius: 0.55)
        }
    }

    // MARK: - Bar Chart

    private var barChart: some View {
        Chart {
            ForEach(config.series) { series in
                ForEach(series.points) { point in
                    BarMark(
                        x: .value("Category", point.label),
                        y: .value("Value", point.value)
                    )
                    .foregroundStyle(series.color)
                }
            }
        }
        .chartXAxisLabel(config.xAxisLabel)
        .chartYAxisLabel(config.yAxisLabel)
        .chartYAxis { yAxisContent }
    }

    // MARK: - Line Chart

    private var lineChart: some View {
        Chart {
            ForEach(config.series) { series in
                ForEach(series.points) { point in
                    LineMark(
                        x: .value("Category", point.label),
                        y: .value("Value", point.value)
                    )
                    .foregroundStyle(series.color)

                    PointMark(
                        x: .value("Category", point.label),
                        y: .value("Value", point.value)
                    )
                    .foregroundStyle(series.color)
                }
            }
        }
        .chartXAxisLabel(config.xAxisLabel)
        .chartYAxisLabel(config.yAxisLabel)
        .chartYAxis { yAxisContent }
    }

    // MARK: - Area Chart

    private var areaChart: some View {
        Chart {
            ForEach(config.series) { series in
                ForEach(series.points) { point in
                    AreaMark(
                        x: .value("Category", point.label),
                        y: .value("Value", point.value)
                    )
                    .foregroundStyle(series.color.opacity(0.3))

                    LineMark(
                        x: .value("Category", point.label),
                        y: .value("Value", point.value)
                    )
                    .foregroundStyle(series.color)
                }
            }
        }
        .chartXAxisLabel(config.xAxisLabel)
        .chartYAxisLabel(config.yAxisLabel)
        .chartYAxis { yAxisContent }
    }

    // MARK: - Scatter Chart

    private var scatterChart: some View {
        let xLabel = config.xAxisLabel.isEmpty ? "X" : config.xAxisLabel
        let yLabel = config.yAxisLabel.isEmpty ? "Y" : config.yAxisLabel

        return Chart {
            ForEach(config.series) { series in
                ForEach(series.points) { point in
                    PointMark(
                        x: .value(xLabel, point.value),
                        y: .value(yLabel, point.secondaryValue ?? 0)
                    )
                    .foregroundStyle(series.color)
                    .symbolSize(40)
                }
            }
        }
        .chartYAxis { yAxisContent }
    }

    // MARK: - Sector Chart (Pie / Donut)

    private func sectorChart(innerRadius: Double) -> some View {
        let points = indexedPoints(from: config.series.first)
        let scheme = config.colorScheme

        return Chart(points) { pt in
            SectorMark(
                angle: .value("Value", pt.value),
                innerRadius: .ratio(innerRadius),
                angularInset: 1
            )
            .foregroundStyle(scheme.color(at: pt.index))
        }
    }

    // MARK: - Y Axis

    @AxisContentBuilder
    private var yAxisContent: some AxisContent {
        if config.showGrid {
            AxisMarks { _ in
                AxisGridLine()
                AxisValueLabel()
            }
        } else {
            AxisMarks { _ in
                AxisValueLabel()
            }
        }
    }

    // MARK: - Legend

    private var legendView: some View {
        HStack(spacing: 12) {
            ForEach(config.series) { series in
                HStack(spacing: 4) {
                    Circle()
                        .fill(series.color)
                        .frame(width: 8, height: 8)
                    Text(series.label)
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    // MARK: - Helpers

    private func indexedPoints(from series: ChartDataSeries?) -> [IndexedPoint] {
        guard let series = series else { return [] }
        return series.points.enumerated().map { index, point in
            IndexedPoint(id: point.id, index: index, label: point.label, value: point.value)
        }
    }
}

// MARK: - Chart Exporter

struct ChartExporter {

    /// Export a chart configuration as a PNG image.
    @MainActor
    static func exportAsPNG(config: ChartConfiguration, size: CGSize = CGSize(width: 800, height: 500)) -> Data? {
        let chartView = ChartRendererView(config: config, height: size.height)
            .frame(width: size.width, height: size.height)
            .padding(20)
            .background(Color.white)

        let renderer = ImageRenderer(content: chartView)
        renderer.scale = 2.0

        guard let nsImage = renderer.nsImage else { return nil }
        guard let tiff = nsImage.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiff) else { return nil }
        return bitmap.representation(using: .png, properties: [:])
    }

    /// Export a chart as SVG (basic implementation).
    @MainActor
    static func exportAsSVG(config: ChartConfiguration, size: CGSize = CGSize(width: 800, height: 500)) -> String {
        let w = Int(size.width)
        let h = Int(size.height)
        let title = escapeXML(config.title)

        var svg = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"\(w)\" height=\"\(h)\" viewBox=\"0 0 \(w) \(h)\">\n"
        svg += "<rect width=\"100%\" height=\"100%\" fill=\"white\"/>\n"
        svg += "<text x=\"\(w / 2)\" y=\"30\" text-anchor=\"middle\" font-family=\"system-ui\" font-size=\"16\" font-weight=\"bold\">\(title)</text>\n"

        let chartArea = CGRect(x: 60, y: 50, width: size.width - 100, height: size.height - 100)

        switch config.type {
        case .bar:
            svg += generateBarSVG(config: config, area: chartArea)
        case .pie, .donut:
            svg += generatePieSVG(config: config, area: chartArea, isDonut: config.type == .donut)
        default:
            svg += generateBarSVG(config: config, area: chartArea)
        }

        svg += "</svg>"
        return svg
    }

    // MARK: - SVG Generators

    private static func generateBarSVG(config: ChartConfiguration, area: CGRect) -> String {
        var svg = ""
        let allPoints = config.series.flatMap(\.points)
        guard !allPoints.isEmpty else { return svg }

        let maxVal = allPoints.map(\.value).max() ?? 1
        let labels = config.series.first?.points.map(\.label) ?? []
        guard !labels.isEmpty else { return svg }
        let barWidth = area.width / CGFloat(labels.count) * 0.7
        let gap = area.width / CGFloat(labels.count) * 0.3
        let seriesCount = CGFloat(max(config.series.count, 1))

        for (i, series) in config.series.enumerated() {
            for (j, point) in series.points.enumerated() {
                let barHeight = CGFloat(point.value / maxVal) * area.height
                let x = area.minX + CGFloat(j) * (barWidth + gap) + CGFloat(i) * barWidth / seriesCount
                let y = area.maxY - barHeight
                let w = Int(barWidth / seriesCount)
                svg += "  <rect x=\"\(Int(x))\" y=\"\(Int(y))\" width=\"\(w)\" height=\"\(Int(barHeight))\" fill=\"\(series.colorHex)\" rx=\"2\"/>\n"
            }
        }

        for (j, label) in labels.enumerated() {
            let x = area.minX + CGFloat(j) * (barWidth + gap) + barWidth / 2
            svg += "  <text x=\"\(Int(x))\" y=\"\(Int(area.maxY + 18))\" text-anchor=\"middle\" font-family=\"system-ui\" font-size=\"10\" fill=\"#666\">\(escapeXML(label))</text>\n"
        }

        return svg
    }

    private static func generatePieSVG(config: ChartConfiguration, area: CGRect, isDonut: Bool) -> String {
        var svg = ""
        let points = config.series.first?.points ?? []
        let total = points.map(\.value).reduce(0, +)
        guard total > 0 else { return svg }

        let cx = area.midX
        let cy = area.midY
        let r = min(area.width, area.height) / 2 - 10
        let innerR: CGFloat = isDonut ? r * 0.55 : 0
        let scheme = config.colorScheme
        var startAngle: Double = -(.pi / 2)

        for (i, point) in points.enumerated() {
            let sliceAngle = (point.value / total) * 2 * .pi
            let endAngle = startAngle + sliceAngle
            let x1 = cx + CGFloat(cos(startAngle)) * r
            let y1 = cy + CGFloat(sin(startAngle)) * r
            let x2 = cx + CGFloat(cos(endAngle)) * r
            let y2 = cy + CGFloat(sin(endAngle)) * r
            let largeArc = sliceAngle > .pi ? 1 : 0
            let hex = scheme.color(at: i).toHex() ?? "#007AFF"

            if isDonut {
                let ix1 = cx + CGFloat(cos(endAngle)) * innerR
                let iy1 = cy + CGFloat(sin(endAngle)) * innerR
                let ix2 = cx + CGFloat(cos(startAngle)) * innerR
                let iy2 = cy + CGFloat(sin(startAngle)) * innerR
                svg += "  <path d=\"M \(f(x1)) \(f(y1)) A \(f(r)) \(f(r)) 0 \(largeArc) 1 \(f(x2)) \(f(y2)) L \(f(ix1)) \(f(iy1)) A \(f(innerR)) \(f(innerR)) 0 \(largeArc) 0 \(f(ix2)) \(f(iy2)) Z\" fill=\"\(hex)\"/>\n"
            } else {
                svg += "  <path d=\"M \(f(cx)) \(f(cy)) L \(f(x1)) \(f(y1)) A \(f(r)) \(f(r)) 0 \(largeArc) 1 \(f(x2)) \(f(y2)) Z\" fill=\"\(hex)\"/>\n"
            }

            startAngle = endAngle
        }

        return svg
    }

    private static func f(_ v: CGFloat) -> String {
        String(format: "%.1f", v)
    }

    private static func escapeXML(_ str: String) -> String {
        str.replacingOccurrences(of: "&", with: "&amp;")
           .replacingOccurrences(of: "<", with: "&lt;")
           .replacingOccurrences(of: ">", with: "&gt;")
    }
}
