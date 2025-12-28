import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "APIClient")

/// Standard API response envelope matching backend SuccessResponse<T>
/// Note: timestamp is optional as some endpoints don't include it
struct SuccessResponse<T: Decodable>: Decodable {
    let success: Bool
    let data: T
    let message: String?
    let timestamp: String?
}

/// Standard API error response
struct ErrorResponse: Decodable {
    let success: Bool
    let errorCode: String
    let message: String
    let details: [String: String]?
    let timestamp: String
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case success
        case errorCode = "error_code"
        case message
        case details
        case timestamp
        case requestId = "request_id"
    }
}

/// Shared HTTP client with auth header injection
final class ApiClient {
    static let shared = ApiClient()

    private let session: URLSession
    private let baseURL: String
    private let decoder: JSONDecoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30.0
        config.timeoutIntervalForResource = 60.0

        // Register network firewall protocol
        config.protocolClasses = [NetworkFirewallProtocol.self]

        self.session = URLSession(configuration: config)

        // Read from environment or default to localhost
        // Use centralized API configuration (handles environment, HTTPS enforcement, etc.)
        self.baseURL = APIConfiguration.shared.baseURL

        self.decoder = JSONDecoder()
        // Don't use automatic snake_case conversion - models use explicit CodingKeys
        // self.decoder.keyDecodingStrategy = .convertFromSnakeCase
    }

    // MARK: - Request Methods

    func request<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        authenticated: Bool = true,
        unwrapEnvelope: Bool = false
    ) async throws -> T {
        let url = try buildURL(endpoint)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Inject auth token if needed
        if authenticated, let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Encode body if present
        if let body = body {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ApiError.invalidResponse
        }

        // Handle auth errors
        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ApiError.unauthorized
        }

        // Handle other errors
        guard (200...299).contains(httpResponse.statusCode) else {
            throw ApiError.httpError(httpResponse.statusCode, data)
        }

        // Decode response (with or without envelope unwrapping)
        do {
            if unwrapEnvelope {
                let envelope = try decoder.decode(SuccessResponse<T>.self, from: data)
                return envelope.data
            } else {
                return try decoder.decode(T.self, from: data)
            }
        } catch {
            // Log raw response for debugging
            if let rawResponse = String(data: data, encoding: .utf8) {
                logger.error("APIClient decode error - Raw response: \(rawResponse.prefix(200))")
            }
            throw ApiError.decodingError(error)
        }
    }

    func upload(
        _ endpoint: String,
        file: Data,
        fileName: String,
        mimeType: String,
        parameters: [String: String] = [:]
    ) async throws -> Data {
        let url = try buildURL(endpoint)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        // Inject auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Build multipart body
        var body = Data()

        // Add parameters
        for (key, value) in parameters {
            body.append("--\(boundary)\r\n")
            body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n")
            body.append("\(value)\r\n")
        }

        // Add file
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(file)
        body.append("\r\n")
        body.append("--\(boundary)--\r\n")

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ApiError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ApiError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw ApiError.httpError(httpResponse.statusCode, data)
        }

        return data
    }

    // MARK: - Convenience Methods

    /// Request with JSON body (dictionary)
    func request<T: Decodable>(
        path: String,
        method: HTTPMethod = .get,
        jsonBody: [String: Any]? = nil,
        authenticated: Bool = true,
        extraHeaders: [String: String]? = nil
    ) async throws -> T {
        let url = try buildURL(path)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if authenticated, let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add extra headers
        if let extraHeaders = extraHeaders {
            for (key, value) in extraHeaders {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }

        if let jsonBody = jsonBody {
            request.httpBody = try JSONSerialization.data(withJSONObject: jsonBody)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ApiError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ApiError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw ApiError.httpError(httpResponse.statusCode, data)
        }

        // Decode response envelope and unwrap data
        let envelope = try decoder.decode(SuccessResponse<T>.self, from: data)
        return envelope.data
    }

    /// Multipart upload returning decoded response
    func multipart<T: Decodable>(
        path: String,
        fileField: String = "file",
        fileURL: URL,
        parameters: [String: String] = [:],
        authenticated: Bool = true,
        extraHeaders: [String: String]? = nil
    ) async throws -> T {
        let fileData = try Data(contentsOf: fileURL)
        let fileName = fileURL.lastPathComponent
        let mimeType = mimeType(for: fileURL)

        let url = try buildURL(path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if authenticated, let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add extra headers
        if let extraHeaders = extraHeaders {
            for (key, value) in extraHeaders {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }

        var body = Data()

        // Add parameters
        for (key, value) in parameters {
            body.append("--\(boundary)\r\n")
            body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n")
            body.append("\(value)\r\n")
        }

        // Add file
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"\(fileField)\"; filename=\"\(fileName)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(fileData)
        body.append("\r\n")
        body.append("--\(boundary)--\r\n")

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ApiError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ApiError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw ApiError.httpError(httpResponse.statusCode, data)
        }

        // Decode response envelope and unwrap data
        let envelope = try decoder.decode(SuccessResponse<T>.self, from: data)
        return envelope.data
    }

    /// Request returning raw Data (for blobs/downloads)
    func requestRaw(
        path: String,
        method: HTTPMethod = .get,
        jsonBody: [String: Any]? = nil,
        authenticated: Bool = true,
        extraHeaders: [String: String]? = nil
    ) async throws -> Data {
        let url = try buildURL(path)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue

        if authenticated, let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add extra headers
        if let extraHeaders = extraHeaders {
            for (key, value) in extraHeaders {
                request.setValue(value, forHTTPHeaderField: key)
            }
        }

        if let jsonBody = jsonBody {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: jsonBody)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ApiError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw ApiError.unauthorized
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw ApiError.httpError(httpResponse.statusCode, data)
        }

        return data
    }

    // MARK: - Streaming Support

    struct StreamingTask {
        let task: URLSessionDataTask
        let cancel: () -> Void
    }

    func makeStreamingTask(
        path: String,
        method: HTTPMethod,
        jsonBody: Encodable,
        onContent: @escaping (String) -> Void,
        onDone: @escaping () -> Void,
        onError: @escaping (Error) -> Void
    ) throws -> StreamingTask {
        let url = try buildURL(path)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.timeoutInterval = 300
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(jsonBody)

        // Per-task delegate to capture stream
        let delegate = StreamingDelegate(
            onContent: onContent,
            onDone: onDone,
            onError: onError
        )
        let streamSession = URLSession(
            configuration: .default,
            delegate: delegate,
            delegateQueue: .main
        )
        let task = streamSession.dataTask(with: request)
        delegate.task = task

        return StreamingTask(
            task: task,
            cancel: {
                task.cancel()
                streamSession.finishTasksAndInvalidate()
            }
        )
    }

    // MARK: - Helpers

    private func buildURL(_ endpoint: String) throws -> URL {
        let path = endpoint.hasPrefix("/") ? endpoint : "/\(endpoint)"
        let urlString = "\(baseURL)\(path)"

        guard let url = URL(string: urlString) else {
            throw ApiError.invalidURL(urlString)
        }

        return url
    }

    private func mimeType(for url: URL) -> String {
        let ext = url.pathExtension.lowercased()
        switch ext {
        case "json": return "application/json"
        case "csv": return "text/csv"
        case "xlsx": return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        case "xls": return "application/vnd.ms-excel"
        case "parquet": return "application/octet-stream"
        default: return "application/octet-stream"
        }
    }
}

// MARK: - Streaming Delegate

private final class StreamingDelegate: NSObject, URLSessionDataDelegate {
    var buffer = Data()
    weak var task: URLSessionDataTask?
    let onContent: (String) -> Void
    let onDone: () -> Void
    let onError: (Error) -> Void

    init(
        onContent: @escaping (String) -> Void,
        onDone: @escaping () -> Void,
        onError: @escaping (Error) -> Void
    ) {
        self.onContent = onContent
        self.onDone = onDone
        self.onError = onError
    }

    func urlSession(
        _ session: URLSession,
        dataTask: URLSessionDataTask,
        didReceive data: Data
    ) {
        buffer.append(data)

        // Split by newline
        while let range = buffer.range(of: Data([0x0a])) { // \n
            let lineData = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
            buffer.removeSubrange(buffer.startIndex...range.lowerBound)

            guard let line = String(data: lineData, encoding: .utf8),
                  line.hasPrefix("data:") else { continue }

            let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)

            // Ignore [START] marker
            if payload == "[START]" { continue }

            guard let jsonData = payload.data(using: .utf8) else { continue }

            do {
                let obj = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any]

                if let content = obj?["content"] as? String, !content.isEmpty {
                    onContent(content)
                }

                if let done = obj?["done"] as? Bool, done == true {
                    onDone()
                }
            } catch {
                // Ignore malformed chunk
            }
        }
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: Error?
    ) {
        if let error = error {
            onError(error)
        } else {
            onDone()
        }
    }
}

// MARK: - Supporting Types

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"
}

enum ApiError: LocalizedError {
    case invalidURL(String)
    case invalidResponse
    case unauthorized
    case httpError(Int, Data)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL(let url):
            return "Invalid URL: \(url)"
        case .invalidResponse:
            return "Invalid server response"
        case .unauthorized:
            return "Unauthorized - please log in again"
        case .httpError(let code, let data):
            if let message = String(data: data, encoding: .utf8), !message.isEmpty {
                return "Server error (\(code)): \(message)"
            }
            return "Server error: \(code)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        }
    }
}

// MARK: - Data Extension

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
