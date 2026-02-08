//
//  FindReplaceBar.swift
//  MagnetarStudio (macOS)
//
//  In-editor find & replace bar with match highlighting.
//  Supports case-sensitive toggle, regex toggle, and match navigation.
//

import SwiftUI

struct FindReplaceBar: View {
    @Binding var isVisible: Bool
    let coordinator: CodeTextView.Coordinator?

    @State private var findQuery = ""
    @State private var replaceQuery = ""
    @State private var showReplace = false
    @State private var caseSensitive = false
    @State private var useRegex = false
    @State private var matchCount = 0
    @State private var currentMatch = 0
    @FocusState private var findFocused: Bool

    var body: some View {
        VStack(spacing: 4) {
            // Find row
            HStack(spacing: 6) {
                HStack(spacing: 4) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)

                    TextField("Find", text: $findQuery)
                        .textFieldStyle(.plain)
                        .font(.system(size: 12))
                        .focused($findFocused)
                        .onSubmit { navigateNext() }
                        .onChange(of: findQuery) { _, _ in updateSearch() }
                }
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .background(RoundedRectangle(cornerRadius: 4).fill(.background))
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.primary.opacity(0.1)))

                // Match count
                Text(matchCount > 0 ? "\(currentMatch + 1)/\(matchCount)" : "No results")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                    .frame(width: 60)

                // Navigation
                Button { navigatePrevious() } label: {
                    Image(systemName: "chevron.up")
                        .font(.system(size: 10, weight: .semibold))
                }
                .buttonStyle(.plain)
                .disabled(matchCount == 0)

                Button { navigateNext() } label: {
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10, weight: .semibold))
                }
                .buttonStyle(.plain)
                .disabled(matchCount == 0)

                // Toggles
                Toggle(isOn: $caseSensitive) {
                    Text("Aa")
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                }
                .toggleStyle(.button)
                .controlSize(.small)
                .onChange(of: caseSensitive) { _, _ in updateSearch() }
                .help("Case Sensitive")

                Toggle(isOn: $useRegex) {
                    Text(".*")
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                }
                .toggleStyle(.button)
                .controlSize(.small)
                .onChange(of: useRegex) { _, _ in updateSearch() }
                .help("Regular Expression")

                // Replace toggle
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        showReplace.toggle()
                    }
                } label: {
                    Image(systemName: showReplace ? "chevron.up.square" : "chevron.down.square")
                        .font(.system(size: 12))
                }
                .buttonStyle(.plain)
                .help("Toggle Replace")

                Spacer()

                // Close
                Button {
                    coordinator?.clearFindHighlights()
                    isVisible = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Replace row
            if showReplace {
                HStack(spacing: 6) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.2.squarepath")
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)

                        TextField("Replace", text: $replaceQuery)
                            .textFieldStyle(.plain)
                            .font(.system(size: 12))
                            .onSubmit { replaceCurrent() }
                    }
                    .padding(.horizontal, 6)
                    .padding(.vertical, 4)
                    .background(RoundedRectangle(cornerRadius: 4).fill(.background))
                    .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.primary.opacity(0.1)))

                    Button("Replace") { replaceCurrent() }
                        .controlSize(.small)
                        .disabled(matchCount == 0)

                    Button("All") { replaceAll() }
                        .controlSize(.small)
                        .disabled(matchCount == 0)

                    Spacer()
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.6))
        .onAppear { findFocused = true }
        .onDisappear { coordinator?.clearFindHighlights() }
    }

    // MARK: - Actions

    private func updateSearch() {
        guard let coordinator else {
            matchCount = 0
            return
        }
        matchCount = coordinator.highlightFindMatches(
            query: findQuery,
            caseSensitive: caseSensitive,
            useRegex: useRegex
        )
        currentMatch = matchCount > 0 ? 0 : 0
        if matchCount > 0 {
            coordinator.scrollToFindMatch(at: 0)
        }
    }

    private func navigateNext() {
        guard matchCount > 0 else { return }
        currentMatch = (currentMatch + 1) % matchCount
        coordinator?.scrollToFindMatch(at: currentMatch)
    }

    private func navigatePrevious() {
        guard matchCount > 0 else { return }
        currentMatch = (currentMatch - 1 + matchCount) % matchCount
        coordinator?.scrollToFindMatch(at: currentMatch)
    }

    private func replaceCurrent() {
        guard matchCount > 0 else { return }
        coordinator?.replaceCurrentMatch(at: currentMatch, with: replaceQuery)
        updateSearch()
    }

    private func replaceAll() {
        coordinator?.replaceAllMatches(with: replaceQuery)
        updateSearch()
    }
}
