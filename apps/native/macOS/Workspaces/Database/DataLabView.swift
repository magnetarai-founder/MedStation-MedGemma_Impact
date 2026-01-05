//
//  DataLabView.swift
//  MagnetarStudio (macOS)
//
//  AI-powered data analysis component for Database Workspace:
//  - Natural Language querying
//  - Pattern discovery
//

import SwiftUI

// MARK: - Data Lab Mode

enum DataLabMode: String, CaseIterable {
    case naturalLanguage = "Ask Questions"
    case patterns = "Find Patterns"

    var icon: String {
        switch self {
        case .naturalLanguage: return "text.bubble"
        case .patterns: return "chart.bar"
        }
    }
}

// MARK: - Combined Data Lab View

struct CombinedDataLabView: View {
    @State private var mode: DataLabMode = .naturalLanguage
    @State private var query: String = ""
    @State private var context: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var nlResponse: NLQueryResponse? = nil
    @State private var patternResults: PatternDiscoveryResult? = nil

    private let dataLabService = DataLabService.shared

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header with mode switcher
                VStack(spacing: 16) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 48))
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    Text("Data Lab")
                        .font(.title.weight(.bold))

                    Text("AI-powered data analysis and insights")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    // Mode Switcher
                    HStack(spacing: 0) {
                        ForEach(DataLabMode.allCases, id: \.self) { labMode in
                            Button(action: {
                                withAnimation(.magnetarStandard) {
                                    mode = labMode
                                    // Clear results when switching modes
                                    query = ""
                                    context = ""
                                    errorMessage = nil
                                    nlResponse = nil
                                    patternResults = nil
                                }
                            }) {
                                HStack(spacing: 6) {
                                    Image(systemName: labMode.icon)
                                        .font(.system(size: 13))
                                    Text(labMode.rawValue)
                                        .font(.system(size: 13, weight: .medium))
                                }
                                .foregroundColor(mode == labMode ? .white : .secondary)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 10)
                                .background(
                                    mode == labMode
                                        ? AnyShapeStyle(LinearGradient.magnetarGradient)
                                        : AnyShapeStyle(Color.gray.opacity(0.1))
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .clipShape(Capsule())
                    .overlay(
                        Capsule()
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                }
                .padding(.top, 32)

                // Mode-specific content
                if mode == .naturalLanguage {
                    naturalLanguageSection
                } else {
                    patternDiscoverySection
                }

                // Error message
                if let error = errorMessage {
                    HStack(spacing: 12) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                    .padding(.horizontal, 32)
                }

                Spacer()
            }
            .frame(maxWidth: 800)
            .frame(maxWidth: .infinity)
        }
    }

    // MARK: - Natural Language Section

    private var naturalLanguageSection: some View {
        VStack(spacing: 24) {
            // Query input
            VStack(alignment: .leading, spacing: 8) {
                Text("Your Question")
                    .font(.system(size: 13, weight: .medium))
                TextEditor(text: $query)
                    .frame(height: 100)
                    .font(.system(size: 14))
                    .padding(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
                    .disabled(isLoading)

                Text("Example: \"What are the top 5 customers by revenue?\"")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 32)

            // Submit button
            Button(action: { Task { await askQuestion() } }) {
                HStack(spacing: 8) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Asking..." : "Ask AI")
                }
                .frame(maxWidth: 300)
            }
            .buttonStyle(.borderedProminent)
            .disabled(query.isEmpty || isLoading)

            // Response area
            if let answer = nlResponse {
                VStack(alignment: .leading, spacing: 16) {
                    Divider()
                        .padding(.horizontal, 32)

                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Answer")
                                .font(.system(size: 15, weight: .semibold))
                            Spacer()
                            if let confidence = answer.confidence {
                                Text("\(Int(confidence * 100))% confident")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color.gray.opacity(0.1))
                                    .cornerRadius(4)
                            }
                        }

                        Text(answer.answer)
                            .font(.system(size: 14))
                            .textSelection(.enabled)
                            .padding(16)
                            .background(Color.surfaceSecondary.opacity(0.5))
                            .cornerRadius(8)

                        if let sources = answer.sources, !sources.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Sources:")
                                    .font(.caption.weight(.medium))
                                    .foregroundColor(.secondary)
                                ForEach(sources, id: \.self) { source in
                                    HStack(spacing: 6) {
                                        Image(systemName: "link")
                                            .font(.caption)
                                        Text(source)
                                            .font(.caption)
                                    }
                                    .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 32)
                }
            }
        }
    }

    // MARK: - Pattern Discovery Section

    private var patternDiscoverySection: some View {
        VStack(spacing: 24) {
            // Input fields
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Query")
                        .font(.system(size: 13, weight: .medium))
                    TextField("Describe what patterns to find", text: $query)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Context (Optional)")
                        .font(.system(size: 13, weight: .medium))
                    TextEditor(text: $context)
                        .frame(height: 80)
                        .font(.system(size: 14))
                        .padding(8)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                        .disabled(isLoading)

                    Text("Additional context to help with pattern detection")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, 32)

            // Submit button
            Button(action: { Task { await discoverPatterns() } }) {
                HStack(spacing: 8) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Analyzing..." : "Discover Patterns")
                }
                .frame(maxWidth: 300)
            }
            .buttonStyle(.borderedProminent)
            .disabled(query.isEmpty || isLoading)

            // Results area
            if let result = patternResults {
                VStack(alignment: .leading, spacing: 16) {
                    Divider()
                        .padding(.horizontal, 32)

                    VStack(alignment: .leading, spacing: 12) {
                        if let summary = result.summary {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Summary")
                                    .font(.system(size: 15, weight: .semibold))
                                Text(summary)
                                    .font(.system(size: 13))
                                    .foregroundColor(.secondary)
                                    .padding(16)
                                    .background(Color.surfaceSecondary.opacity(0.5))
                                    .cornerRadius(8)
                            }
                        }

                        if !result.patterns.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Patterns Found (\(result.patterns.count))")
                                    .font(.system(size: 15, weight: .semibold))

                                ForEach(result.patterns) { pattern in
                                    patternRow(pattern)
                                }
                            }
                        } else {
                            Text("No patterns found")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.horizontal, 32)
                }
            }
        }
    }

    @ViewBuilder
    private func patternRow(_ pattern: PatternDiscoveryResult.Pattern) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(pattern.type)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.blue))

                Spacer()

                Text("\(Int(pattern.confidence * 100))%")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Text(pattern.description)
                .font(.system(size: 13))

            if let examples = pattern.examples, !examples.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(examples.prefix(3), id: \.self) { example in
                        HStack(spacing: 6) {
                            Text("•")
                            Text(example)
                        }
                        .font(.caption)
                        .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding(16)
        .background(Color.gray.opacity(0.08))
        .cornerRadius(10)
    }

    // MARK: - Actions

    @MainActor
    private func askQuestion() async {
        isLoading = true
        errorMessage = nil
        nlResponse = nil

        do {
            nlResponse = try await dataLabService.askNaturalLanguage(query: query)
        } catch {
            errorMessage = "Failed to get answer: \(error.localizedDescription)"
        }

        isLoading = false
    }

    @MainActor
    private func discoverPatterns() async {
        isLoading = true
        errorMessage = nil
        patternResults = nil

        do {
            patternResults = try await dataLabService.discoverPatterns(
                query: query,
                context: context.isEmpty ? nil : context
            )
        } catch {
            errorMessage = "Failed to discover patterns: \(error.localizedDescription)"
        }

        isLoading = false
    }
}
