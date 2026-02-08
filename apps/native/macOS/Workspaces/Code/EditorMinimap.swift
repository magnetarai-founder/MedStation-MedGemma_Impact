//
//  EditorMinimap.swift
//  MagnetarStudio (macOS)
//
//  Condensed code overview panel rendered via Canvas.
//  Shows 1-2px per line with syntax-derived coloring and a viewport indicator.
//  Click/drag scrolls the editor to the corresponding line.
//

import SwiftUI

struct EditorMinimap: View {
    let text: String
    let language: CodeLanguage
    let visibleLineRange: ClosedRange<Int>
    let totalLines: Int
    let onScrollToLine: (Int) -> Void

    private let minimapWidth: CGFloat = 80
    private let lineHeight: CGFloat = 2

    var body: some View {
        GeometryReader { geo in
            let maxVisibleLines = Int(geo.size.height / lineHeight)
            let lines = text.components(separatedBy: "\n")
            let keywords = SyntaxHighlighter.keywords(for: language)
            let builtinTypes = SyntaxHighlighter.builtinTypes(for: language)

            ZStack(alignment: .topLeading) {
                // Code lines
                Canvas { context, size in
                    let lineCount = min(lines.count, maxVisibleLines)
                    for i in 0..<lineCount {
                        let line = lines[i]
                        let trimmed = line.trimmingCharacters(in: .whitespaces)
                        let y = CGFloat(i) * lineHeight
                        let indent = CGFloat(line.count - line.drop(while: { $0 == " " || $0 == "\t" }).count)
                        let x = min(indent * 1.5, 20)
                        let width = min(CGFloat(trimmed.count) * 0.8, size.width - x - 4)

                        guard width > 0 else { continue }

                        let color = lineColor(for: trimmed, keywords: keywords, types: builtinTypes)
                        let rect = CGRect(x: x, y: y, width: width, height: max(lineHeight - 0.5, 1))
                        context.fill(Path(rect), with: .color(color))
                    }
                }

                // Viewport indicator
                let viewportTop = CGFloat(max(visibleLineRange.lowerBound - 1, 0)) * lineHeight
                let viewportHeight = max(CGFloat(visibleLineRange.upperBound - visibleLineRange.lowerBound + 1) * lineHeight, 20)

                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.accentColor.opacity(0.12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 2)
                            .stroke(Color.accentColor.opacity(0.3), lineWidth: 1)
                    )
                    .frame(width: minimapWidth, height: viewportHeight)
                    .offset(y: viewportTop)
            }
            .frame(width: minimapWidth, height: geo.size.height)
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        let clickedLine = Int(value.location.y / lineHeight) + 1
                        let clampedLine = max(1, min(clickedLine, totalLines))
                        onScrollToLine(clampedLine)
                    }
            )
        }
        .frame(width: minimapWidth)
        .background(Color(nsColor: .textBackgroundColor).opacity(0.3))
    }

    // MARK: - Line Coloring

    private func lineColor(for line: String, keywords: [String], types: [String]) -> Color {
        let trimmed = line.trimmingCharacters(in: .whitespaces)

        // Comments — green
        if trimmed.hasPrefix("//") || trimmed.hasPrefix("/*") || trimmed.hasPrefix("*") {
            return Color(nsColor: .systemGreen).opacity(0.6)
        }

        // Strings — red
        if trimmed.hasPrefix("\"") || trimmed.hasPrefix("'") || trimmed.hasPrefix("`") {
            return Color(nsColor: .systemRed).opacity(0.5)
        }

        // Check first word for keywords/types
        let firstWord = String(trimmed.prefix(while: { $0.isLetter || $0 == "_" }))
        if keywords.contains(firstWord) {
            return Color(nsColor: .systemPink).opacity(0.7)
        }
        if types.contains(firstWord) {
            return Color(nsColor: .systemCyan).opacity(0.6)
        }

        // Default — label color
        return Color(nsColor: .labelColor).opacity(0.25)
    }
}
