//
//  ChartBlockView.swift
//  MagnetarStudio (macOS)
//
//  Renders a chart inline in WorkspaceEditor as a block.
//  Click to edit opens ChartBuilderView. Resizable.
//

import SwiftUI
import Charts
import os

struct ChartBlockView: View {
    @Binding var config: ChartConfiguration
    let isFocused: Bool
    let onFocus: () -> Void
    let onDelete: () -> Void

    @State private var showEditor = false
    @State private var isHovered = false
    @State private var chartHeight: CGFloat = 250

    var body: some View {
        VStack(spacing: 0) {
            if config.series.isEmpty {
                emptyState
            } else {
                chartContent
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.surfaceTertiary.opacity(0.5))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(
                    isFocused ? Color.accentColor : (isHovered ? Color.gray.opacity(0.3) : Color.gray.opacity(0.15)),
                    lineWidth: isFocused ? 2 : 1
                )
        )
        .onTapGesture { onFocus() }
        .onHover { isHovered = $0 }
        .sheet(isPresented: $showEditor) {
            ChartBuilderView(
                spreadsheet: nil,
                onInsert: { newConfig in
                    config = newConfig
                    showEditor = false
                },
                onCancel: { showEditor = false }
            )
        }
    }

    // MARK: - Chart Content

    private var chartContent: some View {
        VStack(spacing: 0) {
            ChartRendererView(config: config, height: chartHeight)
                .padding(16)

            // Toolbar on hover
            if isHovered || isFocused {
                Divider()
                HStack(spacing: 8) {
                    Button {
                        showEditor = true
                    } label: {
                        Label("Edit Chart", systemImage: "pencil")
                            .font(.system(size: 11))
                    }
                    .controlSize(.small)

                    Spacer()

                    // Resize controls
                    HStack(spacing: 4) {
                        resizeButton(height: 200, label: "S")
                        resizeButton(height: 300, label: "M")
                        resizeButton(height: 400, label: "L")
                    }

                    Divider().frame(height: 14)

                    Button {
                        exportChart()
                    } label: {
                        Image(systemName: "square.and.arrow.up")
                            .font(.system(size: 11))
                    }
                    .buttonStyle(.plain)
                    .help("Export as PNG")

                    Button {
                        onDelete()
                    } label: {
                        Image(systemName: "trash")
                            .font(.system(size: 11))
                            .foregroundStyle(.red)
                    }
                    .buttonStyle(.plain)
                    .help("Delete chart")
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "chart.bar.doc.horizontal")
                .font(.system(size: 28))
                .foregroundStyle(.tertiary)

            Text("Empty Chart")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(.secondary)

            Button("Configure Chart") {
                showEditor = true
            }
            .controlSize(.small)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 160)
    }

    // MARK: - Helpers

    private func resizeButton(height: CGFloat, label: String) -> some View {
        Button {
            withAnimation(.easeOut(duration: 0.2)) {
                chartHeight = height
            }
        } label: {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(chartHeight == height ? .white : .secondary)
                .frame(width: 22, height: 18)
                .background(
                    RoundedRectangle(cornerRadius: 3)
                        .fill(chartHeight == height ? Color.accentColor : Color.gray.opacity(0.15))
                )
        }
        .buttonStyle(.plain)
    }

    private func exportChart() {
        Task { @MainActor in
            guard let data = ChartExporter.exportAsPNG(config: config) else { return }

            let panel = NSSavePanel()
            panel.allowedContentTypes = [.png]
            panel.nameFieldStringValue = "\(config.title.isEmpty ? "chart" : config.title).png"

            guard panel.runModal() == .OK, let url = panel.url else { return }
            do {
                try data.write(to: url, options: .atomic)
            } catch {
                Logger(subsystem: "com.magnetar.studio", category: "ChartExport")
                    .error("Failed to export chart: \(error.localizedDescription)")
            }
        }
    }
}
