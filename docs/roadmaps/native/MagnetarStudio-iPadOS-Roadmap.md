# MagnetarStudio: iPadOS 26 Roadmap
**Native iPad App - Mobile-First AI Platform**

---

## Vision Statement

MagnetarStudio for iPadOS 26 brings **professional-grade AI workflows to iPad**, designed for:

- **Touch-first interface** - Optimized for multi-touch gestures, Apple Pencil
- **Liquid Glass design** - Gorgeous fluid UI matching macOS 26
- **Apple FM on-device** - Same 3B LLM, zero cloud dependency
- **Neural Engine** - Full access via A19 Pro / M-series chips
- **Stage Manager** - Pro multitasking workflows
- **Universal Control** - Seamless Mac/iPad integration
- **P2P Mesh** - Direct device-to-device collaboration

**Professional AI platform. Anywhere.**

---

## Product Positioning

### MagnetarStudio iPadOS Edition

**Target Audience:**
- Mobile professionals (field work, travel)
- Creative teams (designers, content creators)
- Students & researchers
- iPad Pro users (M4/M5 iPads, iPad Pro 13")
- Privacy-focused mobile users

**Unique Selling Points:**
1. **Full desktop-class AI** - No compromises on iPad
2. **Offline-first mobile** - Work on planes, in field, anywhere
3. **Touch-optimized** - Gestures, Apple Pencil integration
4. **Stage Manager** - Multi-window workflows
5. **Cellular support** - P2P mesh over cellular (future)
6. **Battery efficient** - All-day usage on M4/M5 iPads

**Pricing Strategy:**
- Same premium pricing as macOS ($99-199/year)
- Universal purchase (buy once, use on Mac + iPad)
- Demonstrates feature parity with desktop

---

## Platform-Specific Features

### iPadOS 26 Exclusive Capabilities

#### 1. Touch-First Interface

**Multi-Touch Gestures:**
```swift
// Pinch to zoom in workflow designer
.gesture(
    MagnificationGesture()
        .onChanged { scale in
            canvasZoom = scale
        }
)

// Swipe between workspaces
.gesture(
    DragGesture()
        .onEnded { value in
            if value.translation.width < -100 {
                navigateToNext()
            } else if value.translation.width > 100 {
                navigateToPrevious()
            }
        }
)
```

**Long-Press Menus:**
```swift
// Context menus on long press
.contextMenu {
    Button("Open") { openFile() }
    Button("Share") { shareFile() }
    Button("Delete", role: .destructive) { deleteFile() }
}
```

**Haptic Feedback:**
```swift
// Tactile feedback on interactions
let impact = UIImpactFeedbackGenerator(style: .medium)
impact.impactOccurred()
```

#### 2. Apple Pencil Integration

**Use Cases:**
- Annotate code in agent sessions
- Draw workflow connections
- Highlight query results
- Sketch AI prompts (handwriting → text)
- Sign documents in Vault

**Implementation:**
```swift
import PencilKit

struct AnnotationCanvas: View {
    @State private var canvasView = PKCanvasView()

    var body: some View {
        CanvasView(canvasView: $canvasView)
            .onAppear {
                canvasView.tool = PKInkingTool(.pen, color: .blue, width: 2)
                canvasView.drawingPolicy = .pencilOnly // Finger for pan/zoom
            }
    }
}
```

**Features:**
- Pressure sensitivity for annotations
- Palm rejection (draw with hand resting)
- Double-tap Pencil to switch tools
- Scribble support (handwriting anywhere)

#### 3. Stage Manager & Multitasking

**Stage Manager Support:**
```swift
// Enable multi-window support
@main
struct MagnetarStudioApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowResizability(.contentSize) // Allow window resizing
    }
}
```

**Workflows:**
- Chat window + Database window side-by-side
- Agent session + Code editor split view
- Vault browser + Preview window
- Workflow designer + Execution monitor

**Split View:**
- 50/50 split (two apps)
- 70/30 split (primary/secondary)
- Slide Over (floating overlay)

#### 4. iPad-Specific Layouts

**Compact Layouts:**
- Portrait mode optimized
- Tab bar at bottom (iOS standard)
- Collapsible sidebars
- Sheet presentations for modals

**Adaptive UI:**
```swift
@Environment(\.horizontalSizeClass) var sizeClass

var body: some View {
    if sizeClass == .compact {
        // Portrait: Stack vertically
        VStack {
            NavigationBar()
            ContentView()
        }
    } else {
        // Landscape: Sidebar + content
        NavigationSplitView {
            Sidebar()
        } detail: {
            ContentView()
        }
    }
}
```

#### 5. Keyboard Support

**Magic Keyboard / Smart Keyboard:**
- Full keyboard shortcuts (same as macOS)
- Cmd+Tab app switcher
- Cmd+Space Spotlight
- Hardware ESC key support

**Keyboard Shortcuts:**
```swift
.keyboardShortcut("n", modifiers: .command) // New chat
.keyboardShortcut("t", modifiers: .command) // New query tab
.keyboardShortcut("k", modifiers: .command) // Command palette
```

**On-Screen Keyboard:**
- Accessory bar with SQL keywords (Database workspace)
- Markdown toolbar (Chat workspace)
- Auto-suggestions for file paths

#### 6. Trackpad & Mouse Support

**Pointer Interactions:**
```swift
.hoverEffect() // Highlight on hover
.onHover { isHovering in
    // Change cursor icon
}
```

**Cursor Shapes:**
- Pointer for buttons
- I-beam for text
- Hand for draggable items
- Crosshair for workflow canvas

#### 7. Drag & Drop

**System-Wide Drag & Drop:**
```swift
// Drop files from Files app into Vault
.onDrop(of: [.fileURL], isTargeted: $isTargeted) { providers in
    providers.forEach { provider in
        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier) { item, error in
            if let url = item as? URL {
                uploadFile(url)
            }
        }
    }
    return true
}

// Drag code snippet to Files app
.onDrag {
    NSItemProvider(object: codeSnippet as NSString)
}
```

**Use Cases:**
- Drag files from Files app → Vault
- Drag query results → Numbers/Excel
- Drag code snippets → Notes/Bear
- Drag images → Photos

#### 8. Camera & Photo Library

**Use Cases:**
- Scan documents into Vault (VisionKit OCR)
- Take photo → upload to Vault
- Select from Photo Library → attach to chat
- Scan QR codes for P2P pairing

**Implementation:**
```swift
import PhotosUI
import VisionKit

struct DocumentScanner: View {
    @State private var scannedImage: UIImage?

    var body: some View {
        DocumentCameraView { result in
            switch result {
            case .success(let scan):
                scannedImage = scan.imageOfPage(at: 0)
                uploadToVault(scannedImage)
            case .failure(let error):
                print("Scan failed: \(error)")
            }
        }
    }
}
```

#### 9. Cellular Support

**Offline P2P Mesh:**
- P2P over cellular data
- Low-bandwidth mode
- Sync when on Wi-Fi
- Cellular data usage monitoring

**Future:**
- Direct device-to-device via Bluetooth
- Mesh relay nodes (one device has internet, shares with others)

#### 10. Handoff & Continuity

**Universal Control:**
- Use Mac keyboard/mouse to control iPad
- Drag files between Mac ↔ iPad
- Copy on Mac, paste on iPad

**Handoff:**
```swift
let userActivity = NSUserActivity(activityType: "com.magnetar.chat")
userActivity.title = "Continue Chat"
userActivity.isEligibleForHandoff = true
userActivity.userInfo = ["sessionId": currentSession.id.uuidString]
```

**Workflows:**
- Start chat on iPad → continue on Mac
- Start query on Mac → view results on iPad
- Edit workflow on iPad → deploy from Mac

---

## iPadOS-Specific UI/UX Design

### Touch Targets

**Minimum Sizes:**
- Buttons: 44x44 pt (Apple HIG)
- List rows: 44pt height
- Tab bar items: 48pt height
- Toolbar items: 44pt

**Spacing:**
- Minimum 8pt between interactive elements
- Generous padding for comfortable tapping

### Gestures Library

**Navigation:**
- Swipe left/right: Switch workspaces
- Swipe down: Dismiss modal
- Swipe up: Open command palette
- Pinch: Zoom in/out (workflow canvas, images)
- Two-finger swipe: Navigate back/forward in history

**Interactions:**
- Tap: Select
- Long press: Context menu
- Double-tap: Open file
- Drag: Reorder items, move files
- Rotate: Rotate images/diagrams (two-finger rotate)

### Adaptive Layouts

**Portrait Mode (iPad 11"):**
```
┌─────────────────────┐
│   Navigation Bar    │
├─────────────────────┤
│                     │
│                     │
│   Content Area      │
│                     │
│                     │
│                     │
├─────────────────────┤
│    Tab Bar          │
└─────────────────────┘
```

**Landscape Mode (iPad 13" Pro):**
```
┌────────┬────────────────────────┐
│        │  Navigation Bar        │
│        ├────────────────────────┤
│        │                        │
│ Side   │                        │
│ bar    │   Content Area         │
│        │                        │
│        │                        │
└────────┴────────────────────────┘
```

**Stage Manager (Multiple Windows):**
```
┌──────────┬──────────┬──────────┐
│          │          │          │
│  Chat    │  Agent   │  Vault   │
│          │          │          │
│          │          │          │
└──────────┴──────────┴──────────┘
         Recent apps
```

### Dark Mode (iPad Pro OLED)

**True Black Backgrounds:**
```swift
// Use pure black for OLED power savings
Color(uiColor: .systemBackground) // Adapts to true black on OLED
.background(.black) // Pure black (#000000)
```

**Benefits:**
- Extreme battery savings on OLED displays
- Gorgeous contrast
- Reduced eye strain

---

## Architecture Adjustments for iPadOS

### UIKit vs SwiftUI

**Recommendation: 95% SwiftUI, 5% UIKit**

**SwiftUI for:**
- All main UI (Liquid Glass design)
- Navigation, lists, forms
- Animations, transitions
- Touch gesture handling

**UIKit for:**
- Advanced text editing (UITextView for code editor)
- Camera integration (UIImagePickerController, DocumentCamera)
- Legacy features requiring UIKit APIs

**Hybrid Example:**
```swift
struct CodeEditorView: UIViewRepresentable {
    @Binding var text: String

    func makeUIView(context: Context) -> UITextView {
        let textView = UITextView()
        textView.font = .monospacedSystemFont(ofSize: 14, weight: .regular)
        textView.autocapitalizationType = .none
        textView.autocorrectionType = .no
        textView.keyboardType = .asciiCapable
        return textView
    }

    func updateUIView(_ uiView: UITextView, context: Context) {
        uiView.text = text
    }
}
```

### State Management (Same as macOS)

**@Observable Stores:**
- Same architecture as macOS
- Shared code between platforms
- iPadOS-specific stores:
  - `GestureStore` - Track gesture state
  - `KeyboardStore` - Monitor keyboard visibility
  - `MultitaskingStore` - Stage Manager state

### Performance Considerations

**iPadOS Constraints:**
- Thermal throttling on sustained load (iPad vs Mac)
- Battery life more critical
- Memory limits (6-16GB depending on model)
- Cellular data usage

**Optimizations:**
- Aggressive background task suspension
- Lower MLX model sizes (3B vs 7B)
- Compressed image caching
- Intelligent preloading (Wi-Fi only)

### Device-Specific Features

**Detect iPad Model:**
```swift
import UIKit

enum iPadModel {
    case pro11M4
    case pro13M4
    case air11M2
    case regular10

    static var current: iPadModel {
        // Detect based on screen size, CPU, etc.
    }
}

// Adjust features based on model
if iPadModel.current == .pro13M4 {
    // Enable advanced features (MLX 7B models, Metal 4 ray tracing)
} else {
    // Limit to lightweight features
}
```

---

## Implementation Roadmap (iPadOS-Specific)

### Phase 1: Foundation (Weeks 1-3)

**Differences from macOS:**

#### Week 1: Touch-First Design System

**Tasks:**
- [ ] Create iPadOS SwiftUI target (shares backend code with macOS)
- [ ] Implement touch-friendly Liquid Glass components
  - Larger tap targets (44x44pt minimum)
  - Generous padding
  - Touch feedback (haptics)

- [ ] Design adaptive layouts
  - Portrait mode
  - Landscape mode
  - Split View
  - Slide Over

- [ ] Tab bar navigation (iOS standard)
  ```swift
  TabView(selection: $selectedTab) {
      TeamWorkspace()
          .tabItem {
              Label("Team", systemImage: "person.2")
          }
          .tag(Tab.team)

      ChatWorkspace()
          .tabItem {
              Label("Chat", systemImage: "bubble.left")
          }
          .tag(Tab.chat)

      // ... other tabs
  }
  ```

#### Week 2: Touch Gestures & Authentication

**Tasks:**
- [ ] Implement swipe gestures
  - Swipe to switch tabs
  - Pull to refresh
  - Swipe to delete

- [ ] Face ID / Touch ID authentication
  ```swift
  import LocalAuthentication

  func authenticateUser() async throws {
      let context = LAContext()
      var error: NSError?

      guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
          throw AuthError.biometricsUnavailable
      }

      try await context.evaluatePolicy(
          .deviceOwnerAuthenticationWithBiometrics,
          localizedReason: "Unlock MagnetarStudio"
      )
  }
  ```

- [ ] On-screen keyboard handling
  - Keyboard avoidance (push content up)
  - Dismiss keyboard on scroll
  - Keyboard toolbar

#### Week 3: Apple Pencil & Handwriting

**Tasks:**
- [ ] PencilKit integration
- [ ] Scribble support (handwriting to text)
- [ ] Annotation tools
- [ ] Haptic feedback on Pencil interactions

**Deliverables:**
- Touch-optimized UI
- Biometric authentication
- Apple Pencil support

---

### Phase 2: Core Features (Weeks 4-7)

**Same as macOS, with touch optimizations:**

#### Week 4: Chat (Touch-Optimized)

**Differences:**
- [ ] Touch-friendly message bubbles
- [ ] Swipe to copy message
- [ ] Tap-and-hold for context menu
- [ ] On-screen keyboard with Markdown toolbar
- [ ] Voice input button (speech-to-text)

#### Week 5: Database (Touch-Optimized)

**Differences:**
- [ ] Touch-friendly SQL editor
  - Larger font size (16pt vs 14pt)
  - Syntax highlighting optimized for touch
  - On-screen keyboard with SQL keywords
- [ ] Pinch-to-zoom on results table
- [ ] Swipe columns to scroll horizontally
- [ ] Export via Share Sheet (native iOS)

#### Week 6-7: Vault (Touch-Optimized)

**Differences:**
- [ ] Touch-friendly file browser
  - Grid view for touch (larger thumbnails)
  - Long press for context menu
  - Swipe to delete
- [ ] Drag & drop from Files app
- [ ] Photo/Camera integration
  - Take photo → upload
  - Scan document → OCR → upload
- [ ] Share extension (share to Magnetar from other apps)

---

### Phase 3: Advanced Features (Weeks 8-11)

#### Week 8: Stage Manager & Multitasking

**Tasks:**
- [ ] Multi-window support
  ```swift
  @main
  struct MagnetarStudioApp: App {
      var body: some Scene {
          WindowGroup(id: "chat") {
              ChatWorkspace()
          }

          WindowGroup(id: "agent") {
              AgentWorkspace()
          }

          WindowGroup(id: "vault") {
              VaultWorkspace()
          }
      }
  }
  ```

- [ ] Split View handling
  - Compact layout for narrow widths
  - Expanded layout for wide widths

- [ ] Slide Over support
  - Quick chat overlay
  - File preview overlay

- [ ] Handoff integration

**Deliverables:**
- Multiple windows in Stage Manager
- Smooth multitasking
- Handoff to/from Mac

#### Week 9: P2P Mesh (Cellular Support)

**Tasks:**
- [ ] Network Framework over cellular
- [ ] Low-bandwidth mode
  - Compress data
  - Defer large transfers to Wi-Fi
  - Show data usage estimates

- [ ] Bluetooth fallback (future)

#### Week 10-11: Agent & Workflows (Touch-Optimized)

**Agent Orchestration:**
- [ ] Touch-friendly plan approval
- [ ] Apple Pencil to annotate plans
- [ ] Swipe to approve/reject steps

**Workflow Designer:**
- [ ] Touch-based node editor
  - Drag nodes with finger
  - Pinch to zoom canvas
  - Two-finger pan
  - Apple Pencil for precise connections
- [ ] Simplified node palette (larger icons)

---

### Phase 4: iPad-Specific Features (Weeks 12-14)

#### Week 12: Camera & Document Scanning

**Tasks:**
- [ ] Document Scanner (VisionKit)
  ```swift
  import VisionKit

  struct DocumentScannerView: UIViewControllerRepresentable {
      func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
          let scanner = VNDocumentCameraViewController()
          scanner.delegate = context.coordinator
          return scanner
      }
  }
  ```

- [ ] OCR text extraction
  - Extract text from scanned docs
  - Upload as text file or PDF

- [ ] Photo upload
  - Camera integration
  - Photo library picker
  - Image compression before upload

**Deliverables:**
- Scan documents directly into Vault
- OCR for searchable documents
- Photo uploads

#### Week 13: Widgets & Shortcuts

**Home Screen Widgets:**
```swift
import WidgetKit

struct QuickPromptWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "QuickPrompt", provider: Provider()) { entry in
            QuickPromptWidgetView(entry: entry)
        }
        .configurationDisplayName("Quick AI Prompt")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

**Siri Shortcuts:**
```swift
import Intents

class SendPromptIntent: INIntent {
    @NSManaged public var prompt: String
}

// "Hey Siri, ask Magnetar to analyze this code"
```

**Deliverables:**
- Home screen widgets for quick access
- Siri Shortcuts for voice commands

#### Week 14: Performance & Battery Optimization

**Tasks:**
- [ ] Background task limits
  - Pause non-essential tasks in background
  - Resume on foreground

- [ ] Battery monitoring
  ```swift
  UIDevice.current.isBatteryMonitoringEnabled = true
  let batteryLevel = UIDevice.current.batteryLevel

  if batteryLevel < 0.2 {
      // Enable low-power mode (reduce MLX inference)
  }
  ```

- [ ] Thermal monitoring
  - Reduce GPU usage if device hot
  - Defer heavy ML tasks

- [ ] Adaptive quality
  - Lower image quality on cellular
  - Reduce animation complexity on battery saver

**Deliverables:**
- All-day battery life (8+ hours active use)
- No thermal throttling issues
- Cellular data friendly

---

### Phase 5: Testing & Launch (Weeks 15-16)

**Same as macOS, plus:**

#### iPad-Specific Tests

**Device Testing:**
- [ ] iPad Pro 13" M4 (ProMotion 120Hz)
- [ ] iPad Pro 11" M4
- [ ] iPad Air 11" M2
- [ ] iPad 10th gen (A14)

**Orientation Tests:**
- [ ] Portrait mode
- [ ] Landscape mode
- [ ] Rotation handling

**Multitasking Tests:**
- [ ] Stage Manager (multiple windows)
- [ ] Split View (50/50, 70/30)
- [ ] Slide Over
- [ ] App switcher

**Peripheral Tests:**
- [ ] Magic Keyboard
- [ ] Smart Keyboard Folio
- [ ] Apple Pencil (1st & 2nd gen)
- [ ] Trackpad / Mouse

**Network Tests:**
- [ ] Wi-Fi only
- [ ] Cellular only
- [ ] Offline mode
- [ ] P2P over cellular

---

## iPadOS Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Cold Launch** | < 1.5 seconds | Slower than Mac (thermal limits) |
| **Memory (Idle)** | < 120MB | More overhead than Mac |
| **Memory (Active)** | < 400MB | iPad RAM limits (6-16GB) |
| **Battery (Active)** | < 12% / hour | 8+ hours active use |
| **Battery (Background)** | < 1% / hour | Minimal drain |
| **UI Frame Rate** | 60fps (120fps ProMotion) | Match display refresh rate |
| **Touch Latency** | < 20ms | Instant response |
| **Apple Pencil Latency** | < 9ms | Industry-leading |
| **MLX Inference (M4)** | < 1 second (512 tokens) | Optimized for mobile |
| **Cellular Data (Chat)** | < 50KB / message | Compressed |

---

## iPad-Specific Features Summary

### Advantages Over macOS

1. **Mobility** - Use anywhere (field, travel, couch)
2. **Touch interface** - More intuitive for some tasks
3. **Apple Pencil** - Annotations, handwriting
4. **Camera** - Scan documents, take photos
5. **Cellular** - P2P mesh anywhere
6. **Battery life** - All-day usage
7. **Portability** - Lighter than MacBook
8. **Face ID** - Faster authentication than typing password

### Limitations vs macOS

1. **Performance** - Thermal throttling on sustained load
2. **Screen size** - Smaller than iMac/MacBook (but 13" Pro is decent)
3. **No transparent menu bar** - iOS design language
4. **Keyboard** - On-screen keyboard less efficient than hardware
5. **File system** - More restricted than macOS Finder
6. **Multitasking** - Limited to 3 apps in Stage Manager (vs unlimited on Mac)

### Mitigation Strategies

**For Limitations:**
- **Performance:** Optimize for bursts, defer heavy tasks
- **Screen size:** Adaptive layouts, Stage Manager
- **Keyboard:** Support Magic Keyboard, keyboard shortcuts
- **File system:** Deep Files app integration, drag & drop
- **Multitasking:** Prioritize 2-3 most common workflows

---

## Universal App Strategy

### Shared Code (80%)

**Platform-Agnostic:**
- State management (@Observable stores)
- API client (URLSession)
- Business logic
- Data models (SwiftData)
- Networking (P2P mesh)
- Encryption (CryptoKit)
- ML (Apple FM, MLX, Core ML)

**Single Codebase:**
```
MagnetarStudio/
├── Shared/                    # 80% shared code
│   ├── Stores/
│   ├── Models/
│   ├── Networking/
│   ├── Security/
│   ├── ML/
│   └── Utilities/
│
├── macOS/                     # 20% macOS-specific
│   ├── AppKit Integration/
│   ├── Menu Bar/
│   ├── Keyboard Shortcuts/
│   └── Multi-Window/
│
└── iPadOS/                    # 20% iPadOS-specific
    ├── Touch Gestures/
    ├── Apple Pencil/
    ├── Camera/
    └── Widgets/
```

### Platform Detection

```swift
#if os(macOS)
// macOS-specific code
#elseif os(iOS)
// iPadOS-specific code
#endif
```

### Universal Purchase

**App Store Strategy:**
- Single app bundle
- Buy once, use on Mac + iPad
- Same price for both platforms
- iCloud sync between devices

---

## Success Metrics (iPadOS)

### User Experience
- **Mobile-optimized** - Touch interface feels natural
- **Fast** - Instant responses despite mobile constraints
- **Battery-efficient** - All-day usage
- **Beautiful** - Liquid Glass on iPad is stunning
- **Professional** - Desktop-class workflows on iPad

### Business
- **Universal adoption** - Users buy for Mac, discover iPad version
- **Mobile workflows** - Unlock new use cases (field work, travel)
- **Platform showcase** - Demonstrate iPadOS 26 capabilities
- **Competitive advantage** - No other AI platform this powerful on iPad

---

## Risk Mitigation (iPadOS-Specific)

| Risk | Mitigation |
|------|------------|
| **Performance on older iPads** | Optimize for A14+, graceful degradation |
| **Touch UI complexity** | Extensive user testing, iterate on gestures |
| **Battery drain** | Aggressive optimization, background limits |
| **Cellular data costs** | Low-bandwidth mode, user controls |
| **Keyboard limitations** | Support hardware keyboards, voice input |
| **Storage constraints** | Intelligent caching, cloud storage |

---

## Post-Launch Roadmap (iPadOS)

### Version 1.1 (Q1 2026)
- [ ] Siri Shortcuts expansion
- [ ] Widgets for Lock Screen
- [ ] Focus mode integration
- [ ] Live Activities (for long-running tasks)

### Version 1.2 (Q2 2026)
- [ ] Apple Pencil Pro features (squeeze, barrel roll)
- [ ] Freeform integration (collaboration boards)
- [ ] SharePlay support (collaborative workflows)

### Version 2.0 (Q3 2026)
- [ ] iPhone companion app (view-only)
- [ ] Apple Watch complications (status)
- [ ] AirPlay workflows to Apple TV

---

## Conclusion

MagnetarStudio for iPadOS 26 delivers **desktop-class AI workflows optimized for touch**, bringing:

- Full Apple FM integration (on-device LLM)
- Neural Engine acceleration (M4/M5, A19 Pro)
- Liquid Glass design language
- Touch-first interactions
- Apple Pencil support
- Stage Manager multitasking
- Cellular P2P mesh
- All-day battery life

**Professional AI platform. Anywhere.** 📱

**Timeline:** 16 weeks from start to App Store launch
**Team:** Same Swift developers as macOS (shared codebase)
**Outcome:** Universal app - buy once, use on Mac + iPad, seamless sync

Together with the macOS edition, MagnetarStudio showcases the **best of Apple's ecosystem** for professional AI workflows. 💎
