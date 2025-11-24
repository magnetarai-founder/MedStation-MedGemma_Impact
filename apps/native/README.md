# MagnetarStudio Native App

Native macOS 26 and iPadOS 26 application built with Swift 6 and SwiftUI.

## Structure

```
native/
├── Shared/           # 80% shared code (iOS + macOS)
├── macOS/            # 20% macOS-specific code
├── iPadOS/           # 20% iPadOS-specific code
├── Tests/            # Unit and UI tests
└── Resources/        # Assets, icons, etc.
```

## Requirements

- Xcode 16+
- macOS Tahoe 26+
- Swift 6.2+
- M-series Mac (M3, M4, M5) recommended

## Features

- **Liquid Glass Design** - macOS 26 design language
- **Apple FM Integration** - On-device Foundation Models (3B LLM)
- **MLX Acceleration** - M5 Neural Accelerators
- **Metal 4** - GPU compute and visualization
- **Secure Enclave** - Hardware-level encryption
- **P2P Mesh** - Network Framework + Bonjour

## Getting Started

1. Open `MagnetarStudio.xcodeproj` in Xcode
2. Select target (macOS or iPadOS)
3. Build and run (⌘R)

Backend must be running at `localhost:8000` for full functionality.
