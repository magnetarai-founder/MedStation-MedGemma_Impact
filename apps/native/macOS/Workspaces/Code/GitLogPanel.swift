//
//  GitLogPanel.swift
//  MagnetarStudio (macOS)
//
//  Sidebar panel showing git commit history with inline stat display.
//  Accessed via the gitLog activity bar item in CodeWorkspace.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "GitLog")

struct GitLogPanel: View {
    let workspacePath: String?

    @State private var commits: [GitLogEntry] = []
    @State private var isLoading = false
    @State private var selectedCommitHash: String?
    @State private var selectedCommitStat: String?
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 6) {
                Text("Git Log")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    Task { await loadLog() }
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

            Divider()

            if isLoading && commits.isEmpty {
                VStack {
                    Spacer()
                    ProgressView()
                    Text("Loading...")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .padding(.top, 8)
                    Spacer()
                }
            } else if let error = errorMessage {
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
            } else if commits.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "clock.arrow.circlepath")
                        .font(.system(size: 24))
                        .foregroundStyle(.secondary)
                    Text("No commits yet")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Spacer()
                }
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(commits) { commit in
                            commitRow(commit)

                            if selectedCommitHash == commit.hash, let stat = selectedCommitStat {
                                commitStatView(stat)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .task {
            await loadLog()
        }
    }

    // MARK: - Commit Row

    private func commitRow(_ commit: GitLogEntry) -> some View {
        Button {
            if selectedCommitHash == commit.hash {
                selectedCommitHash = nil
                selectedCommitStat = nil
            } else {
                Task { await showStat(for: commit) }
            }
        } label: {
            HStack(alignment: .top, spacing: 8) {
                // Hash
                Text(commit.hash)
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.purple)
                    .frame(width: 55, alignment: .leading)

                VStack(alignment: .leading, spacing: 2) {
                    // Message
                    Text(commit.message)
                        .font(.system(size: 12))
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    // Author + time
                    HStack(spacing: 4) {
                        Text(commit.author)
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                        Text("·")
                            .foregroundStyle(.tertiary)
                        Text(commit.relativeDate)
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                }

                Spacer()

                if selectedCommitHash == commit.hash {
                    Image(systemName: "chevron.down")
                        .font(.system(size: 8))
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                selectedCommitHash == commit.hash
                    ? Color.accentColor.opacity(0.08)
                    : Color.clear
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private func commitStatView(_ stat: String) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(stat.components(separatedBy: "\n").filter { !$0.isEmpty }, id: \.self) { line in
                Text(line)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 1)
            }
        }
        .padding(.vertical, 4)
        .background(Color.primary.opacity(0.02))
    }

    // MARK: - Git Operations

    private func loadLog() async {
        guard let cwd = workspacePath else {
            errorMessage = "No workspace folder open"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let output = try await runGit(
                ["log", "--oneline", "-50", "--format=%h|%s|%an|%ar"],
                cwd: cwd
            )
            let entries = output.components(separatedBy: "\n")
                .filter { !$0.isEmpty }
                .compactMap { line -> GitLogEntry? in
                    let parts = line.split(separator: "|", maxSplits: 3).map(String.init)
                    guard parts.count >= 4 else { return nil }
                    return GitLogEntry(
                        hash: parts[0],
                        message: parts[1],
                        author: parts[2],
                        relativeDate: parts[3]
                    )
                }
            await MainActor.run {
                commits = entries
                isLoading = false
            }
        } catch {
            logger.warning("Git log failed: \(error)")
            await MainActor.run {
                errorMessage = "Failed to load git log"
                isLoading = false
            }
        }
    }

    private func showStat(for commit: GitLogEntry) async {
        guard let cwd = workspacePath else { return }
        do {
            let output = try await runGit(["show", commit.hash, "--stat", "--format="], cwd: cwd)
            await MainActor.run {
                selectedCommitHash = commit.hash
                selectedCommitStat = output.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        } catch {
            logger.warning("Failed to load commit stat: \(error)")
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
            throw NSError(domain: "GitLog", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: errStr])
        }

        return String(data: outData, encoding: .utf8) ?? ""
    }
}

// MARK: - Model

struct GitLogEntry: Identifiable, Sendable {
    let id = UUID()
    let hash: String
    let message: String
    let author: String
    let relativeDate: String
}
