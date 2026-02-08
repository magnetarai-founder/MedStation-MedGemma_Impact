//
//  SyntaxHighlighter.swift
//  MagnetarStudio (macOS)
//
//  Lightweight keyword-based syntax highlighting for the code editor.
//  Uses NSAttributedString with language-specific keyword sets.
//  Colors are dark-mode aware via NSColor system colors.
//

import AppKit

struct SyntaxHighlighter {
    let language: CodeLanguage

    // MARK: - Color Scheme

    private static let keywordColor = NSColor.systemPink
    private static let typeColor = NSColor.systemCyan
    private static let stringColor = NSColor.systemRed
    private static let commentColor = NSColor.systemGreen.withAlphaComponent(0.7)
    private static let numberColor = NSColor.systemOrange
    private static let defaultColor = NSColor.labelColor

    // MARK: - Highlighting

    func highlight(_ text: String, font: NSFont) -> NSMutableAttributedString {
        let attributed = NSMutableAttributedString(
            string: text,
            attributes: [
                .font: font,
                .foregroundColor: Self.defaultColor
            ]
        )

        let fullRange = NSRange(location: 0, length: (text as NSString).length)
        guard fullRange.length > 0 else { return attributed }

        // Order matters: comments/strings first (they override keywords within them)
        highlightStrings(in: attributed, text: text)
        highlightComments(in: attributed, text: text)
        highlightKeywords(in: attributed, text: text)
        highlightTypes(in: attributed, text: text)
        highlightNumbers(in: attributed, text: text)

        return attributed
    }

    // MARK: - Comments

    private func highlightComments(in attributed: NSMutableAttributedString, text: String) {
        let nsText = text as NSString

        // Single-line comments
        let singleLinePattern: String
        switch language {
        case .python, .ruby:
            singleLinePattern = "#[^\n]*"
        default:
            singleLinePattern = "//[^\n]*"
        }

        applyPattern(singleLinePattern, to: attributed, in: nsText, color: Self.commentColor, priority: true)

        // Multi-line comments (C-style languages)
        switch language {
        case .python:
            // Python triple-quote docstrings
            applyPattern("\"\"\"[\\s\\S]*?\"\"\"", to: attributed, in: nsText, color: Self.commentColor, priority: true)
            applyPattern("'''[\\s\\S]*?'''", to: attributed, in: nsText, color: Self.commentColor, priority: true)
        case .ruby:
            applyPattern("=begin[\\s\\S]*?=end", to: attributed, in: nsText, color: Self.commentColor, priority: true)
        default:
            applyPattern("/\\*[\\s\\S]*?\\*/", to: attributed, in: nsText, color: Self.commentColor, priority: true)
        }
    }

    // MARK: - Strings

    private func highlightStrings(in attributed: NSMutableAttributedString, text: String) {
        let nsText = text as NSString

        // Double-quoted strings (handle escaped quotes)
        applyPattern("\"(?:[^\"\\\\]|\\\\.)*\"", to: attributed, in: nsText, color: Self.stringColor, priority: false)

        // Single-quoted strings (for languages that use them)
        switch language {
        case .python, .ruby, .javascript, .typescript, .go, .rust, .c, .cpp:
            applyPattern("'(?:[^'\\\\]|\\\\.)*'", to: attributed, in: nsText, color: Self.stringColor, priority: false)
        default:
            break
        }

        // Template literals (JS/TS)
        if language == .javascript || language == .typescript {
            applyPattern("`(?:[^`\\\\]|\\\\.)*`", to: attributed, in: nsText, color: Self.stringColor, priority: false)
        }
    }

    // MARK: - Keywords

    private func highlightKeywords(in attributed: NSMutableAttributedString, text: String) {
        let nsText = text as NSString
        let keywords = Self.keywords(for: language)

        for keyword in keywords {
            // Word boundary matching: keyword must be surrounded by non-word characters
            let pattern = "(?<![\\w])(\(NSRegularExpression.escapedPattern(for: keyword)))(?![\\w])"
            applyPattern(pattern, to: attributed, in: nsText, color: Self.keywordColor, priority: false)
        }
    }

    // MARK: - Types

    private func highlightTypes(in attributed: NSMutableAttributedString, text: String) {
        let nsText = text as NSString
        let types = Self.builtinTypes(for: language)

        for typeName in types {
            let pattern = "(?<![\\w])(\(NSRegularExpression.escapedPattern(for: typeName)))(?![\\w])"
            applyPattern(pattern, to: attributed, in: nsText, color: Self.typeColor, priority: false)
        }

        // Also highlight capitalized identifiers after : or -> (likely type annotations)
        switch language {
        case .swift, .typescript, .rust, .go, .java:
            applyPattern("(?::\\s*|->\\s*)([A-Z][A-Za-z0-9_]*)", to: attributed, in: nsText, color: Self.typeColor, priority: false)
        default:
            break
        }
    }

    // MARK: - Numbers

    private func highlightNumbers(in attributed: NSMutableAttributedString, text: String) {
        let nsText = text as NSString
        // Integer and float literals, hex (0x), binary (0b), octal (0o)
        applyPattern("(?<![\\w\\.])\\b(0[xXbBoO])?[0-9][0-9_]*(\\.[0-9_]+)?([eE][+-]?[0-9]+)?\\b", to: attributed, in: nsText, color: Self.numberColor, priority: false)
    }

    // MARK: - Pattern Application

    private func applyPattern(
        _ pattern: String,
        to attributed: NSMutableAttributedString,
        in nsText: NSString,
        color: NSColor,
        priority: Bool
    ) {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else { return }
        let fullRange = NSRange(location: 0, length: nsText.length)

        regex.enumerateMatches(in: nsText as String, options: [], range: fullRange) { match, _, _ in
            guard let matchRange = match?.range else { return }

            if priority {
                // Comments/strings always win
                attributed.addAttribute(.foregroundColor, value: color, range: matchRange)
            } else {
                // Only apply if the range hasn't been colored by a higher-priority rule
                // Check if the first character is still the default color
                if matchRange.location < nsText.length {
                    let existingColor = attributed.attribute(.foregroundColor, at: matchRange.location, effectiveRange: nil) as? NSColor
                    if existingColor == Self.commentColor || existingColor == Self.stringColor {
                        return // Already colored by comment/string
                    }
                }
                attributed.addAttribute(.foregroundColor, value: color, range: matchRange)
            }
        }
    }

    // MARK: - Keyword Lists

    static func keywords(for language: CodeLanguage) -> [String] {
        switch language {
        case .swift:
            return ["import", "func", "class", "struct", "enum", "protocol", "extension", "actor",
                    "let", "var", "if", "else", "guard", "switch", "case", "default", "for", "while",
                    "repeat", "return", "throw", "throws", "try", "catch", "do", "break", "continue",
                    "where", "in", "as", "is", "nil", "true", "false", "self", "Self", "super",
                    "init", "deinit", "subscript", "typealias", "associatedtype", "static", "private",
                    "public", "internal", "fileprivate", "open", "override", "final", "mutating",
                    "nonmutating", "lazy", "weak", "unowned", "async", "await", "some", "any",
                    "@State", "@Binding", "@Published", "@Observable", "@MainActor", "@Environment",
                    "@AppStorage", "@ObservationIgnored"]
        case .python:
            return ["import", "from", "def", "class", "if", "elif", "else", "for", "while",
                    "return", "yield", "try", "except", "finally", "raise", "with", "as",
                    "pass", "break", "continue", "and", "or", "not", "in", "is", "None",
                    "True", "False", "lambda", "global", "nonlocal", "del", "assert", "async", "await"]
        case .javascript, .typescript:
            return ["import", "export", "from", "function", "class", "const", "let", "var",
                    "if", "else", "for", "while", "do", "switch", "case", "default", "break",
                    "continue", "return", "throw", "try", "catch", "finally", "new", "delete",
                    "typeof", "instanceof", "in", "of", "this", "super", "null", "undefined",
                    "true", "false", "async", "await", "yield", "void", "extends", "implements",
                    "interface", "type", "enum", "namespace", "abstract", "readonly"]
        case .rust:
            return ["fn", "let", "mut", "const", "static", "struct", "enum", "impl", "trait",
                    "type", "mod", "use", "pub", "crate", "self", "super", "if", "else",
                    "match", "for", "while", "loop", "break", "continue", "return", "as",
                    "ref", "move", "async", "await", "unsafe", "where", "true", "false"]
        case .go:
            return ["package", "import", "func", "type", "struct", "interface", "map", "chan",
                    "var", "const", "if", "else", "for", "range", "switch", "case", "default",
                    "break", "continue", "return", "go", "defer", "select", "fallthrough",
                    "nil", "true", "false", "make", "new", "append", "len", "cap"]
        case .c, .cpp:
            return ["include", "define", "ifdef", "ifndef", "endif", "if", "else", "for",
                    "while", "do", "switch", "case", "default", "break", "continue", "return",
                    "void", "int", "char", "float", "double", "long", "short", "unsigned",
                    "signed", "static", "const", "extern", "typedef", "struct", "enum", "union",
                    "sizeof", "NULL", "true", "false",
                    // C++ additions
                    "class", "namespace", "using", "template", "virtual", "override", "new",
                    "delete", "public", "private", "protected", "try", "catch", "throw",
                    "auto", "nullptr", "constexpr", "noexcept"]
        case .java:
            return ["import", "package", "class", "interface", "enum", "extends", "implements",
                    "public", "private", "protected", "static", "final", "abstract", "synchronized",
                    "void", "int", "char", "float", "double", "long", "short", "byte", "boolean",
                    "if", "else", "for", "while", "do", "switch", "case", "default", "break",
                    "continue", "return", "throw", "throws", "try", "catch", "finally",
                    "new", "this", "super", "null", "true", "false", "instanceof"]
        case .ruby:
            return ["def", "end", "class", "module", "if", "elsif", "else", "unless", "case",
                    "when", "while", "until", "for", "do", "begin", "rescue", "ensure", "raise",
                    "return", "yield", "break", "next", "redo", "retry", "self", "super",
                    "nil", "true", "false", "and", "or", "not", "in", "require", "include",
                    "attr_reader", "attr_writer", "attr_accessor", "puts", "print"]
        case .unknown:
            return []
        }
    }

    static func builtinTypes(for language: CodeLanguage) -> [String] {
        switch language {
        case .swift:
            return ["String", "Int", "Double", "Float", "Bool", "Array", "Dictionary", "Set",
                    "Optional", "Result", "UUID", "URL", "Data", "Date", "Error", "Void",
                    "CGFloat", "NSColor", "NSFont", "NSView", "View", "Color", "Text",
                    "Image", "Button", "HStack", "VStack", "ZStack", "List", "ForEach",
                    "NavigationView", "ScrollView", "Binding", "State", "ObservableObject"]
        case .python:
            return ["str", "int", "float", "bool", "list", "dict", "set", "tuple",
                    "None", "bytes", "range", "object", "type", "Exception"]
        case .typescript:
            return ["string", "number", "boolean", "object", "any", "void", "never",
                    "unknown", "undefined", "null", "Array", "Promise", "Map", "Set",
                    "Record", "Partial", "Required", "Readonly", "Pick", "Omit"]
        case .javascript:
            return ["Array", "Object", "String", "Number", "Boolean", "Map", "Set",
                    "Promise", "Date", "Error", "RegExp", "JSON", "Math", "console"]
        case .rust:
            return ["i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32",
                    "u64", "u128", "usize", "f32", "f64", "bool", "char", "str",
                    "String", "Vec", "Box", "Rc", "Arc", "Option", "Result", "HashMap"]
        case .go:
            return ["int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16",
                    "uint32", "uint64", "float32", "float64", "bool", "string", "byte",
                    "rune", "error", "complex64", "complex128"]
        case .c, .cpp:
            return ["int", "char", "float", "double", "void", "long", "short", "unsigned",
                    "bool", "size_t", "string", "vector", "map", "set", "pair",
                    "shared_ptr", "unique_ptr", "optional", "variant", "tuple"]
        case .java:
            return ["String", "Integer", "Long", "Double", "Float", "Boolean", "Character",
                    "Object", "List", "Map", "Set", "ArrayList", "HashMap", "HashSet",
                    "Optional", "Stream", "Collection", "Iterable", "Comparable"]
        case .ruby:
            return ["String", "Integer", "Float", "Array", "Hash", "Symbol", "Range",
                    "Regexp", "Proc", "Lambda", "IO", "File", "Dir", "Struct", "Class"]
        case .unknown:
            return []
        }
    }
}
