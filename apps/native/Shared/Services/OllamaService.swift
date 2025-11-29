import Foundation

/// Service for managing Ollama server lifecycle
@MainActor
final class OllamaService {
    static let shared = OllamaService()

    private init() {}

    // MARK: - Server Control

    /// Check if Ollama is running
    func checkStatus() async -> Bool {
        do {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
            process.arguments = ["-x", "ollama"]

            let pipe = Pipe()
            process.standardOutput = pipe

            try process.run()
            process.waitUntilExit()

            return process.terminationStatus == 0
        } catch {
            print("Failed to check Ollama status: \(error)")
            return false
        }
    }

    /// Start Ollama server
    func start() async throws {
        // Try common Ollama installation paths
        let possiblePaths = [
            "/opt/homebrew/bin/ollama",  // Apple Silicon Homebrew
            "/usr/local/bin/ollama",      // Intel Homebrew
            "/usr/bin/ollama"             // System install
        ]

        var ollamaPath: String?
        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path) {
                ollamaPath = path
                break
            }
        }

        guard let ollamaPath = ollamaPath else {
            throw OllamaError.startFailed
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: ollamaPath)
        process.arguments = ["serve"]

        // Run in background
        try process.run()

        // Give it a moment to start
        try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
    }

    /// Stop Ollama server
    func stop() async throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        process.arguments = ["-x", "ollama"]

        try process.run()
        process.waitUntilExit()

        if process.terminationStatus != 0 {
            throw OllamaError.stopFailed
        }
    }

    /// Restart Ollama server
    func restart() async throws {
        try await stop()
        try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        try await start()
    }
}

// MARK: - Errors

enum OllamaError: LocalizedError {
    case stopFailed
    case startFailed

    var errorDescription: String? {
        switch self {
        case .stopFailed:
            return "Failed to stop Ollama server"
        case .startFailed:
            return "Failed to start Ollama server"
        }
    }
}
