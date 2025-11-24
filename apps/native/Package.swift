// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MagnetarStudio",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "MagnetarStudio",
            targets: ["MagnetarStudioApp"]
        )
    ],
    targets: [
        // Main macOS app target
        .executableTarget(
            name: "MagnetarStudioApp",
            dependencies: ["MagnetarShared"],
            path: "macOS",
            exclude: ["Info.plist"]
        ),

        // Shared code (80% shared between macOS/iOS)
        .target(
            name: "MagnetarShared",
            path: "Shared"
        ),

        // Tests
        .testTarget(
            name: "MagnetarStudioTests",
            dependencies: ["MagnetarShared"],
            path: "Tests"
        ),
    ]
)
