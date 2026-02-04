//
//  PlatformImage.swift
//  MagnetarStudio
//
//  Cross-platform image type alias for macOS/iOS compatibility.
//

import Foundation

#if canImport(UIKit)
import UIKit
public typealias PlatformImage = UIImage
#elseif canImport(AppKit)
import AppKit
public typealias PlatformImage = NSImage
#endif

// MARK: - Cross-Platform Image Extensions

extension PlatformImage {
    /// Get JPEG data from the image (cross-platform)
    func jpegDataCrossPlatform(compressionQuality: CGFloat) -> Data? {
        #if canImport(UIKit)
        return jpegData(compressionQuality: compressionQuality)
        #elseif canImport(AppKit)
        guard let tiffData = tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: tiffData) else {
            return nil
        }
        return bitmap.representation(using: .jpeg, properties: [.compressionFactor: compressionQuality])
        #endif
    }

    /// Get CGImage from platform image
    var cgImageCrossPlatform: CGImage? {
        #if canImport(UIKit)
        return cgImage
        #elseif canImport(AppKit)
        return cgImage(forProposedRect: nil, context: nil, hints: nil)
        #endif
    }

    /// Get image size
    var sizeCrossPlatform: CGSize {
        #if canImport(UIKit)
        return size
        #elseif canImport(AppKit)
        return size
        #endif
    }
}
