//
//  FileUpload.swift
//  MagnetarStudio
//
//  File upload component matching React FileUpload.tsx specs
//  - Idle state: Dashed border dropzone with upload icon
//  - Loaded state: Card showing filename, size, row/col counts with clear button
//

import SwiftUI
import UniformTypeIdentifiers

struct FileUpload: View {
    @Environment(DatabaseStore.self) private var databaseStore
    @State private var isHovered = false
    @State private var isDragging = false
    @State private var loadedFile: LoadedFile?
    @State private var isUploading = false

    var body: some View {
        VStack(spacing: 0) {
            if isUploading {
                // Uploading state: Show spinner
                uploadingView
            } else if let file = loadedFile {
                // Loaded state: Show file info
                loadedFileCard(file)
            } else {
                // Idle state: Dropzone
                dropZone
            }
        }
        .padding(16)
        .padding(.bottom, 12)
        .background(Color.clear)
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.2))
                .frame(height: 1),
            alignment: .bottom
        )
    }

    // MARK: - Uploading State

    private var uploadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Uploading file...")
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(40)
    }

    // MARK: - Drop Zone (Idle State)

    private var dropZone: some View {
        VStack(spacing: 16) {
            // Upload icon
            Image(systemName: "arrow.up.doc")
                .font(.system(size: 32))
                .foregroundColor(isHovered ? Color.magnetarPrimary : .secondary)

            // Label
            VStack(spacing: 4) {
                Text("Drop file or click to upload")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.primary)

                // Format badges
                HStack(spacing: 6) {
                    FormatBadge(text: "Excel")
                    FormatBadge(text: "CSV")
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(
                    style: StrokeStyle(lineWidth: 2, dash: [6, 4])
                )
                .foregroundColor(isHovered ? Color.magnetarPrimary.opacity(0.6) : Color.gray.opacity(0.3))
        )
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isHovered ? Color.magnetarPrimary.opacity(0.05) : Color.clear)
        )
        .onHover { hovering in
            isHovered = hovering
        }
        .onDrop(of: [.fileURL], isTargeted: $isDragging) { providers in
            handleDrop(providers: providers)
        }
        .onTapGesture {
            openFilePicker()
        }
        .onChange(of: databaseStore.currentFile == nil) { _, isNil in
            if isNil { loadedFile = nil }
        }
    }

    // MARK: - Loaded File Card

    private func loadedFileCard(_ file: LoadedFile) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            // Top row: filename + clear button
            HStack(spacing: 8) {
                Image(systemName: "doc.text")
                    .font(.system(size: 16))
                    .foregroundColor(.secondary)

                Text(file.name)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .foregroundColor(.primary)

                Spacer()

                Button {
                    loadedFile = nil
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .padding(4)
                }
                .buttonStyle(.plain)
                .help("Clear file")
            }

            // Info rows
            HStack(spacing: 16) {
                Text("\(file.rows) × \(file.cols)")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)

                Text(file.sizeFormatted)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    // MARK: - Helpers

    private func handleDrop(providers: [NSItemProvider]) -> Bool {
        guard let provider = providers.first else { return false }

        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { [self] item, error in
            guard let data = item as? Data,
                  let url = URL(dataRepresentation: data, relativeTo: nil) else { return }

            Task { @MainActor in
                loadFile(at: url)
            }
        }

        return true
    }

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.commaSeparatedText, .data]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        panel.begin { response in
            guard response == .OK, let url = panel.url else { return }
            loadFile(at: url)
        }
    }

    private func loadFile(at url: URL) {
        isUploading = true

        Task {
            // Load file metadata asynchronously
            let (fileSize, rows, cols) = await Task.detached {
                let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
                let (rowCount, colCount) = Self.detectFileMetadata(url: url)
                return (size, rowCount, colCount)
            }.value

            await MainActor.run {
                loadedFile = LoadedFile(
                    name: url.lastPathComponent,
                    rows: rows,
                    cols: cols,
                    sizeBytes: fileSize
                )
                isUploading = false
            }
        }
    }

    // MARK: - File Metadata Detection

    private static nonisolated func detectFileMetadata(url: URL) -> (rows: Int, cols: Int) {
        guard let contents = try? String(contentsOf: url, encoding: .utf8) else {
            return (0, 0)
        }

        let lines = contents.components(separatedBy: .newlines).filter { !$0.isEmpty }
        guard !lines.isEmpty else { return (0, 0) }

        // Detect delimiter (CSV or TSV)
        let firstLine = lines[0]
        let delimiter: Character = firstLine.contains("\t") ? "\t" : ","

        // Count columns from first line
        let columns = firstLine.split(separator: delimiter).count

        // Count rows (excluding header)
        let rows = max(lines.count - 1, 0)

        return (rows, columns)
    }
}

// MARK: - Format Badge

struct FormatBadge: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .medium))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(
                Capsule()
                    .fill(Color.blue.opacity(0.1))
            )
            .foregroundColor(.blue)
    }
}

// MARK: - Loaded File Model

struct LoadedFile {
    let name: String
    let rows: Int
    let cols: Int
    let sizeBytes: Int

    var sizeFormatted: String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(sizeBytes))
    }
}

// MARK: - Preview

#Preview {
    FileUpload()
        .environment(DatabaseStore.shared)
        .frame(width: 320)
        .padding()
}
