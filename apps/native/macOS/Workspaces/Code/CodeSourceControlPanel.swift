//
//  CodeSourceControlPanel.swift
//  MagnetarStudio (macOS)
//
//  Sidebar panel for git source control operations.
//  Uses local `git` via Process — works offline without backend.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SourceControl")

struct CodeSourceControlPanel: View {
    let workspacePath: String?
    let onSelectFile: (String) -> Void

    @State private var currentBranch: String = ""
    @State private var changedFiles: [GitFileStatus] = []
    @State private var commitMessage: String = ""
    @State private var isLoading: Bool = false
    @State private var isCommitting: Bool = false
    @State private var errorMessage: String?
    @State private var successMessage: String?
    @State private var selectedFileDiff: String?
    @State private var selectedDiffFileName: String?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Source Control")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()

                Button {
                    Task { await refreshStatus() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .disabled(isLoading)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            // Branch indicator
            if !currentBranch.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: "arrow.triangle.branch")
                        .font(.system(size: 10))
                        .foregroundStyle(.purple)
                    Text(currentBranch)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.primary)
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.bottom, 6)
            }

            Divider()

            if let error = errorMessage {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 24))
                        .foregroundStyle(.orange)
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    Spacer()
                }
            } else if isLoading && changedFiles.isEmpty {
                VStack {
                    Spacer()
                    ProgressView()
                    Text("Loading...")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .padding(.top, 8)
                    Spacer()
                }
            } else {
                // Commit section
                commitSection

                Divider()

                // Changed files
                if changedFiles.isEmpty {
                    VStack(spacing: 8) {
                        Spacer()
                        Image(systemName: "checkmark.circle")
                            .font(.system(size: 24))
                            .foregroundStyle(.green)
                        Text("No changes")
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                } else {
                    changedFilesList
                }

                // Inline diff view
                if let diff = selectedFileDiff, let name = selectedDiffFileName {
                    Divider()

                    HStack(spacing: 6) {
                        Text("Diff")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button {
                            guard let cwd = workspacePath else { return }
                            let fullPath = (cwd as NSString).appendingPathComponent(name)
                            onSelectFile(fullPath)
                        } label: {
                            HStack(spacing: 3) {
                                Image(systemName: "doc.text")
                                    .font(.system(size: 9))
                                Text("Open in Editor")
                                    .font(.system(size: 10))
                            }
                            .foregroundStyle(.secondary)
                        }
                        .buttonStyle(.plain)

                        Button {
                            selectedFileDiff = nil
                            selectedDiffFileName = nil
                        } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 9))
                                .foregroundStyle(.secondary)
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 4)

                    CodeDiffView(diffOutput: diff, fileName: name)
                        .frame(maxHeight: 300)
                }
            }
        }
        .task {
            await refreshStatus()
        }
    }

    // MARK: - Commit Section

    private var commitSection: some View {
        VStack(spacing: 8) {
            TextEditor(text: $commitMessage)
                .font(.system(size: 12))
                .frame(height: 60)
                .scrollContentBackground(.hidden)
                .padding(6)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.primary.opacity(0.04))
                )
                .overlay(alignment: .topLeading) {
                    if commitMessage.isEmpty {
                        Text("Commit message...")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 10)
                            .allowsHitTesting(false)
                    }
                }

            HStack {
                if let success = successMessage {
                    Text(success)
                        .font(.system(size: 10))
                        .foregroundStyle(.green)
                        .lineLimit(1)
                }

                Spacer()

                Button {
                    Task { await stageAll() }
                } label: {
                    Text("Stage All")
                        .font(.system(size: 11))
                }
                .buttonStyle(.plain)
                .disabled(stagedCount == changedFiles.count || changedFiles.isEmpty)

                Button {
                    Task { await commitChanges() }
                } label: {
                    HStack(spacing: 4) {
                        if isCommitting {
                            ProgressView()
                                .scaleEffect(0.5)
                        }
                        Text("Commit")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(
                        RoundedRectangle(cornerRadius: 5)
                            .fill(commitMessage.isEmpty || stagedCount == 0 ? Color.gray.opacity(0.2) : Color.accentColor)
                    )
                    .foregroundStyle(commitMessage.isEmpty || stagedCount == 0 ? Color.secondary : Color.white)
                }
                .buttonStyle(.plain)
                .disabled(commitMessage.isEmpty || stagedCount == 0 || isCommitting)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var stagedCount: Int {
        changedFiles.filter(\.isStaged).count
    }

    // MARK: - Changed Files List

    private var changedFilesList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                // Staged section
                let staged = changedFiles.filter(\.isStaged)
                if !staged.isEmpty {
                    sectionHeader("Staged Changes", count: staged.count)
                    ForEach(staged) { file in
                        fileRow(file)
                    }
                }

                // Unstaged section
                let unstaged = changedFiles.filter { !$0.isStaged }
                if !unstaged.isEmpty {
                    sectionHeader("Changes", count: unstaged.count)
                    ForEach(unstaged) { file in
                        fileRow(file)
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }

    private func sectionHeader(_ title: String, count: Int) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)
            Spacer()
            Text("\(count)")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.tertiary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 4)
    }

    private func fileRow(_ file: GitFileStatus) -> some View {
        HStack(spacing: 6) {
            // Status badge
            Text(file.status.badge)
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(file.status.color)
                .frame(width: 14)

            // File name
            Button {
                guard let cwd = workspacePath else { return }
                let fullPath = (cwd as NSString).appendingPathComponent(file.path)
                onSelectFile(fullPath)
            } label: {
                Text(file.fileName)
                    .font(.system(size: 12))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
            .buttonStyle(.plain)

            Spacer()

            // View diff button
            if file.status != .untracked {
                Button {
                    Task { await loadDiff(for: file) }
                } label: {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 10))
                        .foregroundStyle(selectedDiffFileName == file.path ? .accentColor : .secondary)
                        .frame(width: 18, height: 18)
                        .background(RoundedRectangle(cornerRadius: 3).fill(Color.primary.opacity(0.05)))
                }
                .buttonStyle(.plain)
                .help("View Diff")
            }

            // Stage/unstage button
            Button {
                Task { await toggleStage(file) }
            } label: {
                Image(systemName: file.isStaged ? "minus" : "plus")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                    .frame(width: 18, height: 18)
                    .background(RoundedRectangle(cornerRadius: 3).fill(Color.primary.opacity(0.05)))
            }
            .buttonStyle(.plain)
            .help(file.isStaged ? "Unstage" : "Stage")
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 3)
    }

    // MARK: - Git Operations

    private func refreshStatus() async {
        guard let cwd = workspacePath else {
            errorMessage = "No workspace folder open"
            return
        }

        isLoading = true
        errorMessage = nil
        successMessage = nil

        do {
            // Check if git is available and this is a repo
            let branch = try await runGit(["branch", "--show-current"], cwd: cwd)
            let statusOutput = try await runGit(["status", "--porcelain"], cwd: cwd)

            let files = parseGitStatus(statusOutput)

            await MainActor.run {
                currentBranch = branch.trimmingCharacters(in: .whitespacesAndNewlines)
                changedFiles = files
                isLoading = false
            }
        } catch {
            logger.warning("Git status failed: \(error)")
            await MainActor.run {
                if error.localizedDescription.contains("not a git repository") {
                    errorMessage = "Not a git repository"
                } else {
                    errorMessage = "Git not available:\n\(error.localizedDescription)"
                }
                isLoading = false
            }
        }
    }

    private func toggleStage(_ file: GitFileStatus) async {
        guard let cwd = workspacePath else { return }
        do {
            if file.isStaged {
                _ = try await runGit(["restore", "--staged", file.path], cwd: cwd)
            } else {
                _ = try await runGit(["add", file.path], cwd: cwd)
            }
            await refreshStatus()
        } catch {
            logger.error("Stage/unstage failed: \(error)")
        }
    }

    private func loadDiff(for file: GitFileStatus) async {
        guard let cwd = workspacePath else { return }
        do {
            let diffArgs: [String]
            if file.isStaged {
                diffArgs = ["diff", "--cached", "--", file.path]
            } else {
                diffArgs = ["diff", "--", file.path]
            }
            let output = try await runGit(diffArgs, cwd: cwd)
            await MainActor.run {
                if output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    selectedFileDiff = nil
                    selectedDiffFileName = nil
                } else {
                    selectedFileDiff = output
                    selectedDiffFileName = file.path
                }
            }
        } catch {
            logger.warning("Failed to load diff for \(file.path): \(error)")
        }
    }

    private func stageAll() async {
        guard let cwd = workspacePath else { return }
        do {
            _ = try await runGit(["add", "-A"], cwd: cwd)
            await refreshStatus()
        } catch {
            logger.error("Stage all failed: \(error)")
        }
    }

    private func commitChanges() async {
        guard let cwd = workspacePath else { return }
        let message = commitMessage.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !message.isEmpty else { return }

        isCommitting = true
        do {
            _ = try await runGit(["commit", "-m", message], cwd: cwd)
            await MainActor.run {
                commitMessage = ""
                successMessage = "Committed successfully"
                isCommitting = false
            }
            await refreshStatus()

            // Clear success message after a delay
            try? await Task.sleep(for: .seconds(3))
            await MainActor.run {
                if successMessage == "Committed successfully" {
                    successMessage = nil
                }
            }
        } catch {
            logger.error("Commit failed: \(error)")
            await MainActor.run {
                errorMessage = "Commit failed: \(error.localizedDescription)"
                isCommitting = false
            }
        }
    }

    private func parseGitStatus(_ output: String) -> [GitFileStatus] {
        let lines = output.components(separatedBy: "\n").filter { !$0.isEmpty }
        return lines.compactMap { line in
            guard line.count >= 3 else { return nil }

            let indexStatus = line[line.startIndex]
            let workTreeStatus = line[line.index(line.startIndex, offsetBy: 1)]
            let path = String(line.dropFirst(3))
            let fileName = (path as NSString).lastPathComponent

            let isStaged = indexStatus != " " && indexStatus != "?"
            let status: GitStatus

            if indexStatus == "?" {
                status = .untracked
            } else if indexStatus == "A" || workTreeStatus == "A" {
                status = .added
            } else if indexStatus == "D" || workTreeStatus == "D" {
                status = .deleted
            } else if indexStatus == "R" || workTreeStatus == "R" {
                status = .renamed
            } else {
                status = .modified
            }

            return GitFileStatus(path: path, fileName: fileName, status: status, isStaged: isStaged)
        }
    }

    private func runGit(_ args: [String], cwd: String) async throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["git", "-C", cwd] + args
        process.currentDirectoryURL = URL(fileURLWithPath: cwd)

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        try process.run()
        let outData = outPipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
            let errStr = String(data: errData, encoding: .utf8) ?? "Unknown error"
            throw GitError.commandFailed(errStr)
        }

        return String(data: outData, encoding: .utf8) ?? ""
    }
}

// MARK: - Models

struct GitFileStatus: Identifiable, Sendable {
    let id = UUID()
    let path: String
    let fileName: String
    let status: GitStatus
    let isStaged: Bool
}

enum GitStatus: String, Sendable {
    case modified = "M"
    case added = "A"
    case deleted = "D"
    case untracked = "?"
    case renamed = "R"

    var badge: String { rawValue }

    var color: Color {
        switch self {
        case .modified: return .orange
        case .added: return .green
        case .deleted: return .red
        case .untracked: return .gray
        case .renamed: return .blue
        }
    }
}

private enum GitError: LocalizedError {
    case commandFailed(String)

    var errorDescription: String? {
        switch self {
        case .commandFailed(let msg): return msg
        }
    }
}
