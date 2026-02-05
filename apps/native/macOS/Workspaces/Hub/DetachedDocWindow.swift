//
//  DetachedDocWindow.swift
//  MagnetarStudio
//
//  Pop-out window for editing a document independently.
//

import SwiftUI
import PDFKit

struct DetachedDocEditWindow: View {
    let info: DetachedDocEditInfo
    @State private var document: WorkspaceDocument?
    @State private var editorContent = ""

    var body: some View {
        VStack(spacing: 0) {
            if let doc = document {
                // Toolbar
                HStack {
                    Text(doc.title)
                        .font(.system(size: 14, weight: .semibold))
                    Spacer()
                    Text("\(doc.wordCount) words")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(Color.surfaceTertiary.opacity(0.5))

                Divider()

                // Editor
                ScrollView {
                    WorkspaceEditor(content: $editorContent)
                        .frame(maxWidth: 750)
                        .padding(.horizontal, 40)
                        .padding(.vertical, 24)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .onChange(of: editorContent) { _, newValue in
                    document?.updateContent(newValue)
                    saveDocument()
                }
            } else {
                ProgressView("Loading document...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(Color.surfacePrimary)
        .task {
            loadDocument()
        }
    }

    private func loadDocument() {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/docs", isDirectory: true)
        let file = dir.appendingPathComponent("\(info.id.uuidString).json")

        if let doc = PersistenceHelpers.load(WorkspaceDocument.self, from: file, label: "detached document") {
            document = doc
            editorContent = doc.content
        } else {
            var doc = WorkspaceDocument(id: info.id, title: info.title)
            doc.content = ""
            document = doc
            editorContent = ""
        }
    }

    private func saveDocument() {
        guard let doc = document else { return }
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/docs", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "detached docs")
        let file = dir.appendingPathComponent("\(doc.id.uuidString).json")
        PersistenceHelpers.save(doc, to: file, label: "detached document '\(doc.title)'")
    }
}

// MARK: - Detached Sheet Window

struct DetachedSheetWindow: View {
    let info: DetachedSheetInfo
    @State private var sheet: SpreadsheetDocument?
    @State private var selectedCell: CellAddress?
    @State private var editingCell: CellAddress?
    @State private var formulaText = ""

    var body: some View {
        VStack(spacing: 0) {
            if var loadedSheet = sheet {
                SheetsToolbar(
                    document: Binding(
                        get: { loadedSheet },
                        set: { loadedSheet = $0; sheet = $0 }
                    ),
                    selectedCell: $selectedCell,
                    formulaText: $formulaText,
                    onFormulaCommit: {
                        guard let cell = selectedCell else { return }
                        loadedSheet.setCell(at: cell, value: formulaText)
                        sheet = loadedSheet
                        saveSheet()
                    }
                )

                Divider()

                SpreadsheetGrid(
                    document: Binding(
                        get: { loadedSheet },
                        set: { loadedSheet = $0; sheet = $0 }
                    ),
                    selectedCell: $selectedCell,
                    editingCell: $editingCell
                )
            } else {
                ProgressView("Loading spreadsheet...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(Color.surfacePrimary)
        .task {
            loadSheet()
        }
    }

    private func loadSheet() {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/sheets", isDirectory: true)
        let file = dir.appendingPathComponent("\(info.id.uuidString).json")

        if let s = PersistenceHelpers.load(SpreadsheetDocument.self, from: file, label: "detached spreadsheet") {
            sheet = s
        } else {
            sheet = SpreadsheetDocument(id: info.id, title: info.title)
        }
    }

    private func saveSheet() {
        guard let s = sheet else { return }
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/sheets", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "detached sheets")
        let file = dir.appendingPathComponent("\(s.id.uuidString).json")
        PersistenceHelpers.save(s, to: file, label: "detached spreadsheet '\(s.title)'")
    }
}

// MARK: - Detached PDF Window

struct DetachedPDFViewWindow: View {
    let info: DetachedPDFViewInfo

    var body: some View {
        VStack(spacing: 0) {
            // Simple toolbar
            HStack {
                Text(info.title)
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            if let pdf = PDFDocument(url: info.fileURL) {
                PDFViewWrapper(document: pdf)
            } else {
                Text("Could not load PDF")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(Color.surfacePrimary)
    }
}
