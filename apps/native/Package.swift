// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MedStation",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "MedStation",
            targets: ["MedStation"]
        )
    ],
    targets: [
        // Single target: macOS + Shared code in one module
        .executableTarget(
            name: "MedStation",
            path: ".",
            exclude: [
                "macOS/Info.plist",
                "macOS/Assets.xcassets",
                "MagnetarStudio.xcodeproj",
                "Tests",
                "build",
                ".build"
            ],
            sources: ["macOS", "Shared"]
        ),

        // Tests
        .testTarget(
            name: "MedStationTests",
            dependencies: ["MedStation"],
            path: "Tests"
        ),
    ]
)
