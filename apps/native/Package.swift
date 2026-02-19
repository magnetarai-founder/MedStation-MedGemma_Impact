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
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift-lm", from: "2.25.0"),
    ],
    targets: [
        // Single target: macOS + Shared code in one module
        .executableTarget(
            name: "MedStation",
            dependencies: [
                .product(name: "MLXLLM", package: "mlx-swift-lm"),
                .product(name: "MLXVLM", package: "mlx-swift-lm"),
                .product(name: "MLXLMCommon", package: "mlx-swift-lm"),
            ],
            path: ".",
            exclude: [
                "macOS/Info.plist",
                "macOS/Assets.xcassets",
                "MedStation.xcodeproj",
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
