import Foundation

/// Described object from AI analysis
struct DescribedObject: Codable, Sendable {
    let name: String
    let objectDescription: String
    let position: String
    let prominence: String

    init(
        name: String,
        objectDescription: String = "",
        position: String = "center",
        prominence: String = "background"
    ) {
        self.name = name
        self.objectDescription = objectDescription
        self.position = position
        self.prominence = prominence
    }

    // Custom coding keys to map objectDescription to description for JSON compatibility
    enum CodingKeys: String, CodingKey {
        case name
        case objectDescription = "description"
        case position
        case prominence
    }
}

/// Structured output for image descriptions
struct StructuredImageDescription: Codable, Sendable {
    let caption: String
    let detailedDescription: String
    let scenes: [String]
    let activities: [String]
    let objects: [DescribedObject]
    let colors: [String]
    let mood: String
    let timeOfDay: String?
    let textContent: String?
    let suggestedTags: [String]
    let safetyFlags: [String]

    init(
        caption: String = "",
        detailedDescription: String = "",
        scenes: [String] = [],
        activities: [String] = [],
        objects: [DescribedObject] = [],
        colors: [String] = [],
        mood: String = "neutral",
        timeOfDay: String? = nil,
        textContent: String? = nil,
        suggestedTags: [String] = [],
        safetyFlags: [String] = []
    ) {
        self.caption = caption
        self.detailedDescription = detailedDescription
        self.scenes = scenes
        self.activities = activities
        self.objects = objects
        self.colors = colors
        self.mood = mood
        self.timeOfDay = timeOfDay
        self.textContent = textContent
        self.suggestedTags = suggestedTags
        self.safetyFlags = safetyFlags
    }

    /// Empty description for error cases
    static let empty = StructuredImageDescription()

    /// Generate a summary for AI context
    var contextSummary: String {
        var parts: [String] = []

        parts.append("Caption: \(caption)")

        if !scenes.isEmpty {
            parts.append("Scene: \(scenes.joined(separator: ", "))")
        }

        if !activities.isEmpty {
            parts.append("Activities: \(activities.joined(separator: ", "))")
        }

        if !objects.isEmpty {
            let objectNames = objects.map { $0.name }.joined(separator: ", ")
            parts.append("Objects: \(objectNames)")
        }

        if let text = textContent, !text.isEmpty {
            parts.append("Visible text: \(text)")
        }

        return parts.joined(separator: "\n")
    }
}
