//
//  FormulaEngine.swift
//  MagnetarStudio
//
//  Formula parser and evaluator for spreadsheet cells.
//  Supports: basic math, cell references, ranges, and functions.
//

import Foundation

struct FormulaEngine {
    let cells: [String: SpreadsheetCell]

    // MARK: - Public API

    func evaluate(_ formula: String) -> String {
        guard formula.hasPrefix("=") else { return formula }
        let expr = String(formula.dropFirst()).trimmingCharacters(in: .whitespaces)
        guard !expr.isEmpty else { return "" }

        do {
            let result = try evaluateExpression(expr)
            return formatResult(result)
        } catch let error as FormulaError {
            return error.displayString
        } catch {
            return "#ERROR"
        }
    }

    // MARK: - Expression Evaluation

    private func evaluateExpression(_ expr: String) throws -> Double {
        let trimmed = expr.trimmingCharacters(in: .whitespaces)

        // Check for function calls: FUNC(args)
        if let funcResult = try evaluateFunction(trimmed) {
            return funcResult
        }

        // Try to parse as simple math expression
        return try parseMathExpression(trimmed)
    }

    // MARK: - Functions

    private func evaluateFunction(_ expr: String) throws -> Double? {
        // Pattern: FUNCNAME(args)
        guard let parenStart = expr.firstIndex(of: "("),
              let parenEnd = expr.lastIndex(of: ")"),
              parenEnd > parenStart else {
            return nil
        }

        let funcName = String(expr[expr.startIndex..<parenStart]).uppercased().trimmingCharacters(in: .whitespaces)
        let argsStr = String(expr[expr.index(after: parenStart)..<parenEnd])

        guard !funcName.isEmpty else { return nil }

        let values: [Double]

        // Check if argument is a range (e.g., A1:B10)
        if argsStr.contains(":") && !argsStr.contains(",") {
            values = try resolveRange(argsStr.trimmingCharacters(in: .whitespaces))
        } else {
            // Comma-separated arguments
            let args = splitTopLevel(argsStr, separator: ",")
            values = try args.map { try evaluateExpression($0) }
        }

        switch funcName {
        case "SUM":
            return values.reduce(0, +)
        case "AVERAGE", "AVG":
            guard !values.isEmpty else { return 0 }
            return values.reduce(0, +) / Double(values.count)
        case "COUNT":
            return Double(values.count)
        case "MIN":
            return values.min() ?? 0
        case "MAX":
            return values.max() ?? 0
        case "ABS":
            guard let first = values.first else { return 0 }
            return abs(first)
        case "ROUND":
            guard let first = values.first else { return 0 }
            let places = values.count > 1 ? Int(values[1]) : 0
            let multiplier = pow(10.0, Double(places))
            return (first * multiplier).rounded() / multiplier
        case "IF":
            // IF(condition, trueVal, falseVal) — args must be 3 comma-separated expressions
            let args = splitTopLevel(argsStr, separator: ",")
            guard args.count >= 3 else { throw FormulaError.invalidArgs }
            let condition = try evaluateExpression(args[0])
            return condition != 0 ? try evaluateExpression(args[1]) : try evaluateExpression(args[2])
        case "CONCATENATE", "CONCAT":
            // Return 0 for numeric context — concatenation handled at display level
            return 0
        default:
            throw FormulaError.unknownFunction(funcName)
        }
    }

    // MARK: - Range Resolution

    private func resolveRange(_ rangeStr: String) throws -> [Double] {
        let parts = rangeStr.split(separator: ":").map { String($0).trimmingCharacters(in: .whitespaces) }
        guard parts.count == 2,
              let start = CellAddress.fromString(parts[0]),
              let end = CellAddress.fromString(parts[1]) else {
            throw FormulaError.invalidRange
        }

        var values: [Double] = []
        let minCol = min(start.column, end.column)
        let maxCol = max(start.column, end.column)
        let minRow = min(start.row, end.row)
        let maxRow = max(start.row, end.row)

        for col in minCol...maxCol {
            for row in minRow...maxRow {
                let addr = CellAddress(column: col, row: row)
                if let cell = cells[addr.description], !cell.rawValue.isEmpty {
                    if let num = Double(cell.rawValue) {
                        values.append(num)
                    } else if cell.isFormula {
                        if let num = Double(evaluate(cell.rawValue)) {
                            values.append(num)
                        }
                    }
                }
            }
        }
        return values
    }

    // MARK: - Math Expression Parser

    private func parseMathExpression(_ expr: String) throws -> Double {
        let trimmed = expr.trimmingCharacters(in: .whitespaces)

        // Try as number
        if let num = Double(trimmed) { return num }

        // Try as cell reference
        if let addr = CellAddress.fromString(trimmed) {
            return try resolveCellValue(addr)
        }

        // Handle parentheses
        if trimmed.hasPrefix("(") && trimmed.hasSuffix(")") {
            let inner = String(trimmed.dropFirst().dropLast())
            return try parseMathExpression(inner)
        }

        // Split by + or - (lowest precedence, right to left for subtraction)
        if let idx = findOperator(trimmed, operators: ["+", "-"]) {
            let left = String(trimmed[trimmed.startIndex..<idx])
            let op = trimmed[idx]
            let right = String(trimmed[trimmed.index(after: idx)...])

            if !left.isEmpty {
                let leftVal = try parseMathExpression(left)
                let rightVal = try parseMathExpression(right)
                return op == "+" ? leftVal + rightVal : leftVal - rightVal
            } else if op == "-" {
                // Unary minus
                return -(try parseMathExpression(right))
            }
        }

        // Split by * or /
        if let idx = findOperator(trimmed, operators: ["*", "/"]) {
            let left = String(trimmed[trimmed.startIndex..<idx])
            let right = String(trimmed[trimmed.index(after: idx)...])
            let leftVal = try parseMathExpression(left)
            let rightVal = try parseMathExpression(right)
            if trimmed[idx] == "/" {
                guard rightVal != 0 else { throw FormulaError.divisionByZero }
                return leftVal / rightVal
            }
            return leftVal * rightVal
        }

        // Split by ^
        if let idx = findOperator(trimmed, operators: ["^"]) {
            let left = String(trimmed[trimmed.startIndex..<idx])
            let right = String(trimmed[trimmed.index(after: idx)...])
            return pow(try parseMathExpression(left), try parseMathExpression(right))
        }

        throw FormulaError.parseError
    }

    private func resolveCellValue(_ addr: CellAddress) throws -> Double {
        guard let cell = cells[addr.description], !cell.rawValue.isEmpty else { return 0 }

        if cell.isFormula {
            let result = evaluate(cell.rawValue)
            return Double(result) ?? 0
        }

        return Double(cell.rawValue) ?? 0
    }

    // MARK: - Helpers

    private func findOperator(_ str: String, operators: [Character]) -> String.Index? {
        var depth = 0
        var lastFound: String.Index?

        for i in str.indices {
            let char = str[i]
            if char == "(" { depth += 1 }
            else if char == ")" { depth -= 1 }
            else if depth == 0 && operators.contains(char) {
                // Skip if this is a negative sign at the start or after another operator
                if char == "-" && (i == str.startIndex || "+-*/^(".contains(str[str.index(before: i)])) {
                    continue
                }
                lastFound = i
            }
        }
        return lastFound
    }

    private func splitTopLevel(_ str: String, separator: Character) -> [String] {
        var result: [String] = []
        var current = ""
        var depth = 0

        for char in str {
            if char == "(" { depth += 1 }
            else if char == ")" { depth -= 1 }

            if char == separator && depth == 0 {
                result.append(current.trimmingCharacters(in: .whitespaces))
                current = ""
            } else {
                current.append(char)
            }
        }
        result.append(current.trimmingCharacters(in: .whitespaces))
        return result
    }

    private func formatResult(_ value: Double) -> String {
        if value == value.rounded() && abs(value) < 1e15 {
            return String(format: "%.0f", value)
        }
        return String(format: "%.6g", value)
    }
}

// MARK: - Formula Errors

enum FormulaError: Error {
    case parseError
    case invalidRange
    case invalidArgs
    case divisionByZero
    case unknownFunction(String)
    case circularReference

    var displayString: String {
        switch self {
        case .parseError: return "#PARSE!"
        case .invalidRange: return "#REF!"
        case .invalidArgs: return "#VALUE!"
        case .divisionByZero: return "#DIV/0!"
        case .unknownFunction: return "#NAME?"
        case .circularReference: return "#CIRC!"
        }
    }
}
