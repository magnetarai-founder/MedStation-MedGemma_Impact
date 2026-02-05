//
//  SheetsChartSheet.swift
//  MagnetarStudio (macOS)
//
//  Sheet-specific chart creation: select data range from spreadsheet,
//  pick chart type, customize, and insert as floating overlay or export.
//

import SwiftUI
import Charts

struct SheetsChartSheet: View {
    let document: SpreadsheetDocument
    let onInsert: (ChartConfiguration) -> Void
    let onDismiss: () -> Void

    @State private var config = ChartConfiguration()
    @State private var rangeText = ""
    @State private var orientation: ChartDataExtractor.DataOrientation = .columnsAsSeries
    @State private var autoDetected = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "chart.bar.xaxis")
                    .font(.system(size: 14))
                    .foregroundStyle(Color.accentColor)
                Text("Create Chart from Data")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
                Button { onDismiss() } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(16)

            Divider()

            // Content
            HStack(spacing: 0) {
                // Left: Settings
                settingsPanel
                    .frame(width: 240)

                Divider()

                // Right: Preview
                previewPanel
            }

            Divider()

            // Footer
            HStack {
                Text("\(config.series.count) series, \(config.series.flatMap(\.points).count) data points")
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)

                Spacer()

                Button("Cancel") { onDismiss() }
                    .keyboardShortcut(.cancelAction)

                Button("Insert Chart") {
                    config.sourceRange = rangeText
                    onInsert(config)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(config.series.isEmpty)
            }
            .padding(16)
        }
        .frame(width: 640, height: 480)
        .onAppear { autoDetectRange() }
    }

    // MARK: - Settings

    private var settingsPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                // Range
                VStack(alignment: .leading, spacing: 4) {
                    Text("DATA RANGE")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)

                    TextField("e.g. A1:D10", text: $rangeText)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 12, design: .monospaced))
                        .onChange(of: rangeText) { _, _ in updateChart() }

                    Button("Auto-detect") { autoDetectRange() }
                        .controlSize(.small)
                }

                // Orientation
                VStack(alignment: .leading, spacing: 4) {
                    Text("ORIENTATION")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)

                    Picker("", selection: $orientation) {
                        Text("Columns").tag(ChartDataExtractor.DataOrientation.columnsAsSeries)
                        Text("Rows").tag(ChartDataExtractor.DataOrientation.rowsAsSeries)
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: orientation) { _, _ in updateChart() }
                }

                Divider()

                // Chart type
                VStack(alignment: .leading, spacing: 4) {
                    Text("CHART TYPE")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)

                    ForEach(ChartType.allCases) { type in
                        Button {
                            config.type = type
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: type.icon)
                                    .frame(width: 16)
                                Text(type.rawValue)
                                    .font(.system(size: 12))
                                Spacer()
                                if config.type == type {
                                    Image(systemName: "checkmark")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundStyle(Color.accentColor)
                                }
                            }
                            .padding(.vertical, 4)
                            .padding(.horizontal, 8)
                            .background(
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(config.type == type ? Color.accentColor.opacity(0.08) : Color.clear)
                            )
                            .foregroundStyle(.primary)
                        }
                        .buttonStyle(.plain)
                    }
                }

                Divider()

                // Title
                VStack(alignment: .leading, spacing: 4) {
                    Text("TITLE")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)

                    TextField("Chart title", text: $config.title)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 12))
                }

                // Color scheme
                VStack(alignment: .leading, spacing: 4) {
                    Text("COLORS")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)

                    Picker("", selection: $config.colorScheme) {
                        ForEach(ChartColorScheme.allCases) { scheme in
                            Text(scheme.rawValue).tag(scheme)
                        }
                    }
                    .onChange(of: config.colorScheme) { _, newScheme in
                        applyColorScheme(newScheme)
                    }
                }
            }
            .padding(12)
        }
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Preview

    private var previewPanel: some View {
        VStack {
            if config.series.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: "chart.bar")
                        .font(.system(size: 28))
                        .foregroundStyle(.tertiary)
                    Text("Enter a data range to preview")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ChartRendererView(config: config)
                    .padding(16)
                Spacer()
            }
        }
    }

    // MARK: - Actions

    private func updateChart() {
        guard !rangeText.isEmpty else {
            config.series = []
            return
        }
        config.series = ChartDataExtractor.extract(from: document, range: rangeText, orientation: orientation)
        applyColorScheme(config.colorScheme)
    }

    private func autoDetectRange() {
        let bounds = ChartDataExtractor.dataBounds(document)
        guard bounds.maxRow >= bounds.minRow else { return }

        rangeText = "\(CellAddress.columnLetter(bounds.minCol))\(bounds.minRow + 1):\(CellAddress.columnLetter(bounds.maxCol))\(bounds.maxRow + 1)"
        updateChart()
        autoDetected = true
    }

    private func applyColorScheme(_ scheme: ChartColorScheme) {
        for i in config.series.indices {
            config.series[i].colorHex = scheme.color(at: i).toHex() ?? "#007AFF"
        }
    }
}
