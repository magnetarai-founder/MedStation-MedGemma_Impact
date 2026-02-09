//
//  PDFPanel.swift
//  MagnetarStudio
//
//  PDF viewer panel with sidebar (thumbnails, bookmarks)
//  and annotation toolbar.
//

import SwiftUI
import PDFKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "PDFPanel")

struct PDFPanel: View {
    @State private var pdfDocuments: [PDFDocumentInfo] = []
    @State private var selectedPDFID: UUID?
    @State private var pdfDocument: PDFDocument?
    @State private var searchText = ""
    @FocusState private var isSearchFocused: Bool
    @State private var isLoading = true
    @State private var showThumbnails = true
    @State private var currentPage = 0
    @State private var pdfToDelete: PDFDocumentInfo?
    @State private var saveError: String?

    var body: some View {
        HStack(spacing: 0) {
            // PDF list
            pdfList
                .frame(width: 220)

            Divider()

            // PDF viewer
            if let _ = selectedPDFID, let pdf = pdfDocument {
                VStack(spacing: 0) {
                    // Toolbar
                    pdfToolbar

                    Divider()

                    HStack(spacing: 0) {
                        // Thumbnail sidebar
                        if showThumbnails {
                            PDFThumbnailSidebar(
                                pdfDocument: pdf,
                                currentPage: $currentPage
                            )
                            .frame(width: 140)

                            Divider()
                        }

                        // Main PDF view
                        PDFViewWrapper(document: pdf)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }

                    // Status bar
                    pdfStatusBar
                }
            } else {
                pdfEmptyState
            }
        }
        .task {
            await loadPDFs()
        }
        .onReceive(NotificationCenter.default.publisher(for: .focusPanelSearch)) { _ in
            isSearchFocused = true
        }
        .alert("Delete PDF", isPresented: .constant(pdfToDelete != nil), presenting: pdfToDelete) { pdf in
            Button("Cancel", role: .cancel) { pdfToDelete = nil }
            Button("Delete", role: .destructive) {
                deletePDF(pdf)
                pdfToDelete = nil
            }
        } message: { pdf in
            Text("Are you sure you want to delete '\(pdf.title)'?")
        }
        .alert("Save Error", isPresented: Binding(get: { saveError != nil }, set: { if !$0 { saveError = nil } })) {
            Button("OK") { saveError = nil }
        } message: {
            Text(saveError ?? "Unknown error")
        }
    }

    // MARK: - PDF Toolbar

    private var pdfToolbar: some View {
        HStack(spacing: 8) {
            Button {
                withAnimation(.magnetarQuick) { showThumbnails.toggle() }
            } label: {
                Image(systemName: "sidebar.left")
                    .font(.system(size: 13))
                    .foregroundStyle(showThumbnails ? .primary : .secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Toggle PDF thumbnails")

            Divider().frame(height: 16)

            // Zoom controls
            Button {
            } label: {
                Image(systemName: "minus.magnifyingglass")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Zoom out")

            Button {
            } label: {
                Image(systemName: "plus.magnifyingglass")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Zoom in")

            Divider().frame(height: 16)

            // Annotation tools
            Group {
                annotationButton(icon: "highlighter", help: "Highlight")
                annotationButton(icon: "underline", help: "Underline")
                annotationButton(icon: "note.text", help: "Add Note")
                annotationButton(icon: "pencil.tip", help: "Freehand")
            }

            Spacer()

            // Page indicator
            if let pdf = pdfDocument {
                Text("Page \(currentPage + 1) of \(pdf.pageCount)")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            // More options
            Menu {
                Button("Add Bookmark") {}
                Divider()
                Button("Export Annotations...") {}
                Button("Print...") {}
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .menuStyle(.borderlessButton)
            .frame(width: 28)
            .accessibilityLabel("More PDF options")
        }
        .padding(.horizontal, 12)
        .frame(height: HubLayout.headerHeight)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

    private func annotationButton(icon: String, help: String) -> some View {
        Button {} label: {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .frame(width: 26, height: 26)
        }
        .buttonStyle(.plain)
        .help(help)
        .accessibilityLabel(help)
    }

    // MARK: - Status Bar

    private var pdfStatusBar: some View {
        HStack {
            if let info = pdfDocuments.first(where: { $0.id == selectedPDFID }) {
                Text(info.title)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)

                Divider().frame(height: 12)

                Text(formatFileSize(info.fileSize))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.surfaceTertiary.opacity(0.5))
    }

    // MARK: - PDF List

    private var pdfList: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                TextField("Search PDFs...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .focused($isSearchFocused)

                if !searchText.isEmpty {
                    Button { searchText = "" } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear search")
                }

                Button(action: importPDF) {
                    Image(systemName: "doc.badge.plus")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .frame(width: 24)
                .help("Import PDF")
                .accessibilityLabel("Import PDF")
            }
            .padding(.horizontal, 12)
            .frame(height: HubLayout.headerHeight)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredPDFDocuments.isEmpty {
                VStack(spacing: 8) {
                    Text(searchText.isEmpty ? "No PDFs imported" : "No results")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    if searchText.isEmpty {
                        Button("Import PDF") { importPDF() }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 1) {
                        ForEach(filteredPDFDocuments) { doc in
                            PDFListRow(
                                document: doc,
                                isSelected: selectedPDFID == doc.id,
                                onSelect: { selectPDF(doc) },
                                onDelete: { pdfToDelete = doc }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceTertiary)
    }

    private var filteredPDFDocuments: [PDFDocumentInfo] {
        if searchText.isEmpty { return pdfDocuments }
        let query = searchText.lowercased()
        return pdfDocuments.filter { $0.title.lowercased().contains(query) }
    }

    private var pdfEmptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.viewfinder")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Import a PDF to get started")
                .font(.body)
                .foregroundStyle(.secondary)
            Button("Import PDF") { importPDF() }
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Actions

    private func importPDF() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.pdf]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        guard panel.runModal() == .OK, let url = panel.url else { return }

        // Copy to storage
        let destDir = Self.storageDir
        let destURL = destDir.appendingPathComponent(url.lastPathComponent)

        do {
            if FileManager.default.fileExists(atPath: destURL.path) {
                try FileManager.default.removeItem(at: destURL)
            }
            try FileManager.default.copyItem(at: url, to: destURL)

            let pdf = PDFDocument(url: destURL)
            let attributes = try FileManager.default.attributesOfItem(atPath: destURL.path)
            let info = PDFDocumentInfo(
                title: url.deletingPathExtension().lastPathComponent,
                fileURL: destURL,
                pageCount: pdf?.pageCount ?? 0,
                fileSize: attributes[.size] as? Int64 ?? 0
            )

            pdfDocuments.append(info)
            selectPDF(info)
            saveMetadata()
        } catch {
            logger.error("Failed to import PDF: \(error)")
        }
    }

    private func selectPDF(_ doc: PDFDocumentInfo) {
        selectedPDFID = doc.id
        pdfDocument = PDFDocument(url: doc.fileURL)
        currentPage = 0
    }

    private func deletePDF(_ doc: PDFDocumentInfo) {
        pdfDocuments.removeAll { $0.id == doc.id }
        if selectedPDFID == doc.id {
            selectedPDFID = nil
            pdfDocument = nil
        }
        PersistenceHelpers.remove(at: doc.fileURL, label: "pdf '\(doc.title)'")
        saveMetadata()
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/pdfs", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "pdfs storage")
        return dir
    }

    private static var metadataFile: URL {
        storageDir.appendingPathComponent("_metadata.json")
    }

    private func loadPDFs() async {
        defer { isLoading = false }
        guard let docs = PersistenceHelpers.load([PDFDocumentInfo].self, from: Self.metadataFile, label: "pdf metadata") else { return }
        pdfDocuments = docs.filter { FileManager.default.fileExists(atPath: $0.fileURL.path) }
    }

    private func saveMetadata() {
        do {
            try PersistenceHelpers.trySave(pdfDocuments, to: Self.metadataFile, label: "pdf metadata")
        } catch {
            saveError = "Could not save PDF metadata: \(error.localizedDescription)"
        }
    }

    private func formatFileSize(_ bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: bytes)
    }
}

// MARK: - PDF View Wrapper

struct PDFViewWrapper: NSViewRepresentable {
    let document: PDFDocument

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.document = document
        return view
    }

    func updateNSView(_ nsView: PDFView, context: Context) {
        if nsView.document !== document {
            nsView.document = document
        }
    }
}

// MARK: - PDF Thumbnail Sidebar

struct PDFThumbnailSidebar: View {
    let pdfDocument: PDFDocument
    @Binding var currentPage: Int

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(0..<pdfDocument.pageCount, id: \.self) { index in
                    if let page = pdfDocument.page(at: index) {
                        PDFThumbnailView(page: page, pageNumber: index + 1)
                            .overlay {
                                if currentPage == index {
                                    RoundedRectangle(cornerRadius: 4)
                                        .stroke(Color.magnetarPrimary, lineWidth: 2)
                                }
                            }
                            .onTapGesture {
                                currentPage = index
                            }
                    }
                }
            }
            .padding(8)
        }
        .background(Color.surfaceTertiary)
    }
}

// MARK: - PDF Thumbnail View

struct PDFThumbnailView: View {
    let page: PDFPage
    let pageNumber: Int

    var body: some View {
        VStack(spacing: 4) {
            // Thumbnail image
            let image = page.thumbnail(of: CGSize(width: 120, height: 160), for: .cropBox)
            Image(nsImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(maxWidth: 120, maxHeight: 160)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 4))
                .shadow(color: .black.opacity(0.1), radius: 2, y: 1)

            Text("\(pageNumber)")
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - PDF List Row

private struct PDFListRow: View {
    let document: PDFDocumentInfo
    let isSelected: Bool
    let onSelect: () -> Void
    let onDelete: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: "doc.viewfinder")
                    .font(.system(size: 14))
                    .foregroundStyle(isSelected ? .white : .red)
                    .frame(width: 20)

                VStack(alignment: .leading, spacing: 2) {
                    Text(document.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)
                    Text("\(document.pageCount) pages")
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
