//
//  SheetsPanel.swift
//  MagnetarStudio
//
//  Spreadsheet panel — Excel-like grid with formula engine.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SheetsPanel")

struct SheetsPanel: View {
    @State private var spreadsheets: [SpreadsheetDocument] = []
    @State private var selectedSheetID: UUID?
    @State private var selectedCell: CellAddress?
    @State private var editingCell: CellAddress?
    @State private var formulaText = ""
    @State private var searchText = ""
    @State private var isLoading = true
    @State private var showSheetsList = true
    @State private var showExport = false
    @State private var showTemplatePicker = false
    @State private var selectedTemplate: WorkspaceTemplate?
    @State private var collaborators: [CollaboratorPresence] = []
    @AppStorage("workspace.teamEnabled") private var teamEnabled = false

    var body: some View {
        HStack(spacing: 0) {
            // Sheet list
            if showSheetsList {
                sheetsList
                    .frame(width: 220)
                Divider()
            }

            // Grid area
            if let sheetID = selectedSheetID,
               let sheetIndex = spreadsheets.firstIndex(where: { $0.id == sheetID }) {
                VStack(spacing: 0) {
                    SheetsToolbar(
                        document: $spreadsheets[sheetIndex],
                        selectedCell: $selectedCell,
                        formulaText: $formulaText,
                        onFormulaCommit: { commitFormula(at: sheetIndex) }
                    )

                    // Team collab indicator
                    TeamCollabIndicator(
                        collaborators: collaborators,
                        documentTitle: spreadsheets[sheetIndex].title
                    )

                    Divider()

                    SpreadsheetGrid(
                        document: $spreadsheets[sheetIndex],
                        selectedCell: $selectedCell,
                        editingCell: $editingCell
                    )
                    .onChange(of: selectedCell) { _, newCell in
                        if let cell = newCell {
                            formulaText = spreadsheets[sheetIndex].cell(at: cell).rawValue
                        }
                    }

                    // Status bar
                    sheetStatusBar(at: sheetIndex)
                }
            } else {
                sheetsEmptyState
            }
        }
        .sheet(isPresented: $showTemplatePicker) {
            TemplatePickerSheet(
                targetPanel: .sheet,
                onBlank: {
                    showTemplatePicker = false
                    createSpreadsheet()
                },
                onTemplate: { template in
                    showTemplatePicker = false
                    selectedTemplate = template
                },
                onDismiss: { showTemplatePicker = false }
            )
        }
        .sheet(item: $selectedTemplate) { template in
            TemplateFillSheet(
                template: template,
                onConfirm: { title, variables in
                    let sheet = TemplateStore.shared.instantiateAsSpreadsheet(
                        template: template,
                        title: title,
                        variables: variables
                    )
                    spreadsheets.insert(sheet, at: 0)
                    selectSheet(sheet)
                    saveSheetToDisk(sheet)
                    selectedTemplate = nil
                },
                onCancel: { selectedTemplate = nil }
            )
        }
        .sheet(isPresented: $showExport) {
            if let sheetID = selectedSheetID,
               let sheet = spreadsheets.first(where: { $0.id == sheetID }) {
                ExportSheet(
                    content: .spreadsheet(sheet),
                    onDismiss: { showExport = false }
                )
            }
        }
        .task {
            await loadSpreadsheets()
        }
    }

    // MARK: - Status Bar

    private func sheetStatusBar(at index: Int) -> some View {
        HStack(spacing: 16) {
            // Toggle list
            Button {
                withAnimation(.magnetarQuick) {
                    showSheetsList.toggle()
                }
            } label: {
                Image(systemName: "sidebar.left")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)

            Text(spreadsheets[index].title)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)

            Divider().frame(height: 12)

            Text("\(spreadsheets[index].cells.count) cells")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)

            Spacer()

            // Export button
            Button {
                showExport = true
            } label: {
                Image(systemName: "arrow.up.doc")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .help("Export Spreadsheet")

            if let cell = selectedCell {
                Text("Cell: \(cell.description)")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

    // MARK: - Sheets List

    private var sheetsList: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                TextField("Search sheets...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                Menu {
                    Button("Blank Spreadsheet") { createSpreadsheet() }
                    Button("From Template...") { showTemplatePicker = true }
                } label: {
                    Image(systemName: "plus.rectangle")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .menuStyle(.borderlessButton)
                .frame(width: 24)
                .help("New Spreadsheet")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredSheets.isEmpty {
                VStack(spacing: 8) {
                    Text("No spreadsheets")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    Button("New Spreadsheet") { createSpreadsheet() }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        ForEach(filteredSheets) { sheet in
                            SheetListRow(
                                sheet: sheet,
                                isSelected: selectedSheetID == sheet.id,
                                onSelect: { selectSheet(sheet) },
                                onDelete: { deleteSpreadsheet(sheet) }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceTertiary)
    }

    private var sheetsEmptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "tablecells")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Create or select a spreadsheet")
                .font(.body)
                .foregroundStyle(.secondary)
            Button("New Spreadsheet") { createSpreadsheet() }
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Filtered

    private var filteredSheets: [SpreadsheetDocument] {
        let sorted = spreadsheets.sorted { $0.updatedAt > $1.updatedAt }
        if searchText.isEmpty { return sorted }
        return sorted.filter { $0.title.lowercased().contains(searchText.lowercased()) }
    }

    // MARK: - Actions

    private func createSpreadsheet() {
        let sheet = SpreadsheetDocument()
        spreadsheets.insert(sheet, at: 0)
        selectSheet(sheet)
        saveSheetToDisk(sheet)
    }

    private func selectSheet(_ sheet: SpreadsheetDocument) {
        selectedSheetID = sheet.id
        selectedCell = nil
        editingCell = nil
        formulaText = ""
    }

    private func commitFormula(at sheetIndex: Int) {
        guard let cell = selectedCell else { return }
        let oldValue = spreadsheets[sheetIndex].cell(at: cell).rawValue
        spreadsheets[sheetIndex].setCell(at: cell, value: formulaText)
        saveSheetToDisk(spreadsheets[sheetIndex])

        // Fire automation trigger
        AutomationTriggerService.shared.sheetCellChanged(
            sheetTitle: spreadsheets[sheetIndex].title,
            address: cell.description,
            oldValue: oldValue,
            newValue: formulaText
        )
    }

    private func deleteSpreadsheet(_ sheet: SpreadsheetDocument) {
        spreadsheets.removeAll { $0.id == sheet.id }
        if selectedSheetID == sheet.id {
            selectedSheetID = spreadsheets.first?.id
        }
        deleteSheetFromDisk(sheet)
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/sheets", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "sheets storage")
        return dir
    }

    private func loadSpreadsheets() async {
        defer { isLoading = false }
        let dir = Self.storageDir
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension == "json" }
        } catch {
            logger.error("Failed to list sheets directory: \(error.localizedDescription)")
            return
        }

        var loaded: [SpreadsheetDocument] = []
        for file in files {
            if let sheet = PersistenceHelpers.load(SpreadsheetDocument.self, from: file, label: "spreadsheet") {
                loaded.append(sheet)
            }
        }

        spreadsheets = loaded.sorted { $0.updatedAt > $1.updatedAt }
        selectedSheetID = spreadsheets.first?.id
    }

    private func saveSheetToDisk(_ sheet: SpreadsheetDocument) {
        let file = Self.storageDir.appendingPathComponent("\(sheet.id.uuidString).json")
        PersistenceHelpers.save(sheet, to: file, label: "spreadsheet '\(sheet.title)'")
    }

    private func deleteSheetFromDisk(_ sheet: SpreadsheetDocument) {
        let file = Self.storageDir.appendingPathComponent("\(sheet.id.uuidString).json")
        PersistenceHelpers.remove(at: file, label: "spreadsheet '\(sheet.title)'")
    }
}

// MARK: - Sheet List Row

private struct SheetListRow: View {
    let sheet: SpreadsheetDocument
    let isSelected: Bool
    let onSelect: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: "tablecells")
                    .font(.system(size: 14))
                    .foregroundStyle(isSelected ? .white : Color.green)
                    .frame(width: 20)

                VStack(alignment: .leading, spacing: 2) {
                    Text(sheet.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)
                    Text("\(sheet.cells.count) cells")
                        .font(.system(size: 10))
                        .foregroundStyle(isSelected ? .white.opacity(0.6) : .secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
        .contextMenu {
            Button("Delete", role: .destructive) { onDelete() }
        }
    }
}
