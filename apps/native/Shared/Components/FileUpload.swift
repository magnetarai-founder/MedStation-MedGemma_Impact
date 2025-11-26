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
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
        .onDrop(of: [.fileURL], isTargeted: $isDragging) { providers in
            handleDrop(providers: providers)
        }
        .onTapGesture {
            openFilePicker()
        }
        .onReceive(NotificationCenter.default.publisher(for: .clearWorkspace)) { _ in
            withAnimation {
                loadedFile = nil
            }
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
                    withAnimation {
                        loadedFile = nil
                    }
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

        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, error in
            guard let data = item as? Data,
                  let url = URL(dataRepresentation: data, relativeTo: nil) else { return }

            DispatchQueue.main.async {
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

        if panel.runModal() == .OK, let url = panel.url {
            loadFile(at: url)
        }
    }

    private func loadFile(at url: URL) {
        isUploading = true

        // Simulate async file loading
        DispatchQueue.global(qos: .userInitiated).async {
            // Mock file loading - in real app, parse the file
            let fileSize = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0

            // Simulate processing delay
            Thread.sleep(forTimeInterval: 0.3)

            DispatchQueue.main.async {
                withAnimation {
                    loadedFile = LoadedFile(
                        name: url.lastPathComponent,
                        rows: 1250, // Mock
                        cols: 8,    // Mock
                        sizeBytes: fileSize
                    )
                    isUploading = false
                }
            }
        }
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
        .frame(width: 320)
        .padding()
}
