//
//  ChartBuilderView.swift
//  MagnetarStudio (macOS)
//
//  Full chart builder: type picker, data range selector, axis configuration.
//  Live preview using Swift Charts. Outputs ChartConfiguration.
//

import SwiftUI
import Charts

struct ChartBuilderView: View {
    let spreadsheet: SpreadsheetDocument?
    let onInsert: (ChartConfiguration) -> Void
    let onCancel: () -> Void

    @State private var config = ChartConfiguration()
    @State private var rangeText = ""
    @State private var orientation: ChartDataExtractor.DataOrientation = .columnsAsSeries

    var body: some View {
        HSplitView {
            // Left: Configuration panel
            configPanel
                .frame(minWidth: 260, maxWidth: 280)

            // Right: Live preview
            previewPanel
                .frame(minWidth: 360)
        }
        .frame(width: 720, height: 500)
    }

    // MARK: - Configuration Panel

    private var configPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Chart type picker
                chartTypePicker

                Divider()

                // Data source
                dataSourceSection

                Divider()

                // Axis labels
                axisSection

                Divider()

                // Options
                optionsSection

                Divider()

                // Color scheme
                colorSchemeSection
            }
            .padding(16)
        }
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Chart Type Picker

    private var chartTypePicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("CHART TYPE")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 6) {
                ForEach(ChartType.allCases) { type in
                    chartTypeButton(type)
                }
            }
        }
    }

    private func chartTypeButton(_ type: ChartType) -> some View {
        let isSelected = config.type == type
        return Button {
            config.type = type
        } label: {
            VStack(spacing: 4) {
                Image(systemName: type.icon)
                    .font(.system(size: 16))
                Text(type.rawValue)
                    .font(.system(size: 10, weight: .medium))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.accentColor.opacity(0.15) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(isSelected ? Color.accentColor : Color.gray.opacity(0.2), lineWidth: isSelected ? 2 : 1)
            )
            .foregroundStyle(isSelected ? Color.accentColor : .primary)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Data Source

    private var dataSourceSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("DATA SOURCE")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            if spreadsheet != nil {
                TextField("Cell range (e.g. A1:D10)", text: $rangeText)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12, design: .monospaced))
                    .onChange(of: rangeText) { _, _ in
                        updateFromSpreadsheet()
                    }

                Picker("Orientation", selection: $orientation) {
                    Text("Columns as series").tag(ChartDataExtractor.DataOrientation.columnsAsSeries)
                    Text("Rows as series").tag(ChartDataExtractor.DataOrientation.rowsAsSeries)
                }
                .font(.system(size: 11))
                .onChange(of: orientation) { _, _ in
                    updateFromSpreadsheet()
                }

                Button("Auto-detect range") {
                    autoDetect()
                }
                .controlSize(.small)
            } else {
                Text("No spreadsheet linked")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)

                Text("Add sample data to preview")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)

                Button("Load Sample Data") {
                    loadSampleData()
                }
                .controlSize(.small)
            }
        }
    }

    // MARK: - Axis Labels

    private var axisSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("LABELS")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            TextField("Chart title", text: $config.title)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 12))

            HStack(spacing: 8) {
                TextField("X axis", text: $config.xAxisLabel)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12))
                TextField("Y axis", text: $config.yAxisLabel)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12))
            }
        }
    }

    // MARK: - Options

    private var optionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("OPTIONS")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            Toggle("Show legend", isOn: $config.showLegend)
                .font(.system(size: 12))
            Toggle("Show grid", isOn: $config.showGrid)
                .font(.system(size: 12))
        }
    }

    // MARK: - Color Scheme

    private var colorSchemeSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("COLOR SCHEME")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)

            ForEach(ChartColorScheme.allCases) { scheme in
                Button {
                    config.colorScheme = scheme
                    applyColorScheme(scheme)
                } label: {
                    HStack(spacing: 6) {
                        HStack(spacing: 2) {
                            ForEach(0..<6, id: \.self) { i in
                                Circle()
                                    .fill(scheme.color(at: i))
                                    .frame(width: 10, height: 10)
                            }
                        }

                        Text(scheme.rawValue)
                            .font(.system(size: 11))
                            .foregroundStyle(.primary)

                        Spacer()

                        if config.colorScheme == scheme {
                            Image(systemName: "checkmark")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundStyle(Color.accentColor)
                        }
                    }
                    .padding(.vertical, 4)
                    .padding(.horizontal, 8)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(config.colorScheme == scheme ? Color.accentColor.opacity(0.08) : Color.clear)
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: - Preview Panel

    private var previewPanel: some View {
        VStack(spacing: 0) {
            // Preview header
            HStack {
                Text("Preview")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)

            Divider()

            // Chart preview
            if config.series.isEmpty {
                emptyPreview
            } else {
                ChartRendererView(config: config, height: 300)
                    .padding(20)
            }

            Spacer()

            Divider()

            // Action buttons
            HStack {
                if !config.series.isEmpty {
                    Button("Export PNG") {
                        exportPNG()
                    }
                    .controlSize(.small)
                }

                Spacer()

                Button("Cancel") { onCancel() }
                    .keyboardShortcut(.cancelAction)

                Button("Insert Chart") {
                    config.sourceRange = rangeText.isEmpty ? nil : rangeText
                    onInsert(config)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(config.series.isEmpty)
            }
            .padding(16)
        }
    }

    private var emptyPreview: some View {
        VStack(spacing: 12) {
            Image(systemName: "chart.bar")
                .font(.system(size: 36))
                .foregroundStyle(.tertiary)
            Text("Select a data range or load sample data")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Actions

    private func updateFromSpreadsheet() {
        guard let sheet = spreadsheet, !rangeText.isEmpty else { return }
        config.series = ChartDataExtractor.extract(from: sheet, range: rangeText, orientation: orientation)
    }

    private func autoDetect() {
        guard let sheet = spreadsheet else { return }
        let bounds = ChartDataExtractor.dataBounds(sheet)
        guard bounds.maxRow >= bounds.minRow else { return }

        rangeText = "\(CellAddress.columnLetter(bounds.minCol))\(bounds.minRow + 1):\(CellAddress.columnLetter(bounds.maxCol))\(bounds.maxRow + 1)"
        updateFromSpreadsheet()
    }

    private func loadSampleData() {
        config.title = "Quarterly Sales"
        config.xAxisLabel = "Quarter"
        config.yAxisLabel = "Revenue ($K)"
        config.series = [
            ChartDataSeries(label: "Product A", points: [
                ChartDataPoint(label: "Q1", value: 45),
                ChartDataPoint(label: "Q2", value: 62),
                ChartDataPoint(label: "Q3", value: 58),
                ChartDataPoint(label: "Q4", value: 73)
            ], colorHex: "#007AFF"),
            ChartDataSeries(label: "Product B", points: [
                ChartDataPoint(label: "Q1", value: 32),
                ChartDataPoint(label: "Q2", value: 41),
                ChartDataPoint(label: "Q3", value: 55),
                ChartDataPoint(label: "Q4", value: 48)
            ], colorHex: "#34C759")
        ]
    }

    private func applyColorScheme(_ scheme: ChartColorScheme) {
        for i in config.series.indices {
            let color = scheme.color(at: i)
            config.series[i].colorHex = color.toHex() ?? "#007AFF"
        }
    }

    private func exportPNG() {
        Task { @MainActor in
            guard let data = ChartExporter.exportAsPNG(config: config) else { return }

            let panel = NSSavePanel()
            panel.allowedContentTypes = [.png]
            panel.nameFieldStringValue = "\(config.title.isEmpty ? "chart" : config.title).png"

            guard panel.runModal() == .OK, let url = panel.url else { return }
            try? data.write(to: url)
        }
    }
}
