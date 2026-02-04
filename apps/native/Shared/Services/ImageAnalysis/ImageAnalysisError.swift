import Foundation

/// Errors that can occur during image analysis
enum ImageAnalysisError: LocalizedError {
    case invalidImage
    case modelNotLoaded
    case modelNotAvailable(String)
    case invalidModelURL
    case thermalThrottling
    case analysisTimeout
    case layerFailed(AnalysisLayerType, Error)
    case visionFrameworkError(Error)
    case coreMLError(Error)
    case noLayersEnabled
    case insufficientContext

    var errorDescription: String? {
        switch self {
        case .invalidImage:
            return "The provided image could not be processed"
        case .modelNotLoaded:
            return "The ML model is not loaded"
        case .modelNotAvailable(let name):
            return "Model '\(name)' is not available"
        case .invalidModelURL:
            return "Invalid model download URL"
        case .thermalThrottling:
            return "Device is too hot for full analysis"
        case .analysisTimeout:
            return "Image analysis timed out"
        case .layerFailed(let layer, let error):
            return "\(layer.displayName) failed: \(error.localizedDescription)"
        case .visionFrameworkError(let error):
            return "Vision framework error: \(error.localizedDescription)"
        case .coreMLError(let error):
            return "CoreML error: \(error.localizedDescription)"
        case .noLayersEnabled:
            return "No analysis layers are enabled"
        case .insufficientContext:
            return "Not enough context for structured output generation"
        }
    }

    var recoverySuggestion: String? {
        switch self {
        case .invalidImage:
            return "Try with a different image format"
        case .modelNotLoaded, .modelNotAvailable:
            return "Check your internet connection and try again"
        case .thermalThrottling:
            return "Wait for the device to cool down"
        case .analysisTimeout:
            return "Try with a smaller image or fewer layers"
        case .noLayersEnabled:
            return "Enable at least one analysis layer in settings"
        default:
            return nil
        }
    }
}
