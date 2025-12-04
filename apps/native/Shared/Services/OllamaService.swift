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

    // MARK: - Model Management (via Backend API)

    private var baseURL: String {
        UserDefaults.standard.string(forKey: "apiBaseURL") ?? "http://localhost:8000"
    }

    /// Pull/download a model with streaming progress
    func pullModel(
        modelName: String,
        onProgress: @escaping (OllamaProgress) -> Void,
        onComplete: @escaping (Result<String, Error>) -> Void
    ) {
        // URL encode model name
        guard let encodedName = modelName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            onComplete(.failure(OllamaError.invalidModelName))
            return
        }

        let url = URL(string: "\(baseURL)/api/v1/chat/models/pull/\(encodedName)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Create streaming task
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    onComplete(.failure(error))
                }
                return
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                DispatchQueue.main.async {
                    onComplete(.failure(OllamaError.invalidResponse))
                }
                return
            }

            guard httpResponse.statusCode == 200 else {
                DispatchQueue.main.async {
                    onComplete(.failure(OllamaError.httpError(httpResponse.statusCode)))
                }
                return
            }

            guard let data = data else {
                DispatchQueue.main.async {
                    onComplete(.failure(OllamaError.noData))
                }
                return
            }

            // Parse Server-Sent Events stream
            let dataString = String(data: data, encoding: .utf8) ?? ""
            let lines = dataString.components(separatedBy: "\n")

            for line in lines {
                if line.hasPrefix("data: ") {
                    let jsonString = String(line.dropFirst(6))
                    if let jsonData = jsonString.data(using: .utf8) {
                        do {
                            let progress = try JSONDecoder().decode(OllamaProgress.self, from: jsonData)

                            DispatchQueue.main.async {
                                onProgress(progress)

                                // Call completion on final status
                                if progress.status == "completed" {
                                    onComplete(.success(progress.message))
                                } else if progress.status == "error" {
                                    onComplete(.failure(OllamaError.operationFailed(progress.message)))
                                }
                            }
                        } catch {
                            print("Failed to decode progress: \(error)")
                        }
                    }
                }
            }
        }

        task.resume()
    }

    /// Remove/delete a local model
    func removeModel(modelName: String) async throws -> OllamaOperationResult {
        // URL encode model name
        guard let encodedName = modelName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw OllamaError.invalidModelName
        }

        let url = URL(string: "\(baseURL)/api/v1/chat/models/\(encodedName)")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw OllamaError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw OllamaError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(OllamaOperationResult.self, from: data)
    }

    /// Check installed Ollama version
    func checkVersion() async throws -> OllamaVersion {
        let url = URL(string: "\(baseURL)/api/v1/chat/ollama/version")!
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw OllamaError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw OllamaError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(OllamaVersion.self, from: data)
    }
}

// MARK: - Models

struct OllamaProgress: Codable {
    let status: String  // "progress", "completed", "error"
    let message: String
    let model: String
}

struct OllamaOperationResult: Codable {
    let status: String
    let message: String
    let model: String
}

struct OllamaVersion: Codable {
    let status: String
    let version: String?
    let installed: Bool
    let message: String?
}

// MARK: - Errors

enum OllamaError: LocalizedError {
    case stopFailed
    case startFailed
    case invalidResponse
    case httpError(Int)
    case invalidModelName
    case noData
    case operationFailed(String)

    var errorDescription: String? {
        switch self {
        case .stopFailed:
            return "Failed to stop Ollama server"
        case .startFailed:
            return "Failed to start Ollama server"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .invalidModelName:
            return "Invalid model name"
        case .noData:
            return "No data received from server"
        case .operationFailed(let message):
            return message
        }
    }
}
