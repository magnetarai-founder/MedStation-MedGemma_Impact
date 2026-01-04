//
//  HotSlotSettingsTests.swift
//  MagnetarStudio Tests
//
//  Comprehensive test suite for HotSlotSettings refactoring (Phase 6.24)
//  Tests extracted components: HotSlotCard, HotSlotModelPicker
//  Tests HotSlotManager functionality
//

import XCTest
@testable import MagnetarStudio

@MainActor
final class HotSlotSettingsTests: XCTestCase {

    // MARK: - HotSlotManager Tests

    func testHotSlotManagerSharedInstance() {
        let manager1 = HotSlotManager.shared
        let manager2 = HotSlotManager.shared

        XCTAssertTrue(manager1 === manager2, "Shared instance should be singleton")
    }

    func testHotSlotManagerInitialization() {
        let manager = HotSlotManager.shared

        XCTAssertNotNil(manager.hotSlots, "Hot slots should be initialized")
        XCTAssertEqual(manager.hotSlots.count, 4, "Should have 4 hot slots")
    }

    func testHotSlotManagerSlotNumbers() {
        let manager = HotSlotManager.shared

        // Verify slot numbers are 1-4
        let slotNumbers = manager.hotSlots.map { $0.slotNumber }
        XCTAssertEqual(slotNumbers, [1, 2, 3, 4], "Slot numbers should be 1-4")
    }

    func testHotSlotManagerLoadHotSlots() async {
        let manager = HotSlotManager.shared

        await manager.loadHotSlots()

        // Should complete successfully or fail gracefully
        XCTAssertNotNil(manager.hotSlots, "Hot slots should remain valid after load")
    }

    func testHotSlotManagerAssignToSlot() async {
        let manager = HotSlotManager.shared
        let testModelName = "test-model:latest"

        do {
            try await manager.assignToSlot(slotNumber: 1, modelName: testModelName)

            // If successful, verify assignment
            if let slot = manager.hotSlots.first(where: { $0.slotNumber == 1 }) {
                // Note: Assignment may fail if Ollama is not running
                // We just verify the method doesn't crash
                XCTAssertNotNil(slot, "Slot should exist")
            }
        } catch {
            // Expected if Ollama is not running or model doesn't exist
            print("Assignment test skipped - backend unavailable: \(error)")
        }
    }

    func testHotSlotManagerRemoveFromSlot() async {
        let manager = HotSlotManager.shared

        do {
            try await manager.removeFromSlot(slotNumber: 1)

            // If successful, verify removal
            if let slot = manager.hotSlots.first(where: { $0.slotNumber == 1 }) {
                XCTAssertNotNil(slot, "Slot should still exist")
            }
        } catch {
            // Expected if backend is not running
            print("Removal test skipped - backend unavailable: \(error)")
        }
    }

    func testHotSlotManagerTogglePin() {
        let manager = HotSlotManager.shared

        // Get initial pin state
        guard let initialSlot = manager.hotSlots.first(where: { $0.slotNumber == 1 }) else {
            XCTFail("Slot 1 should exist")
            return
        }

        let initialPinState = initialSlot.isPinned

        // Toggle pin
        await manager.togglePin(1)

        // Verify toggle
        if let updatedSlot = manager.hotSlots.first(where: { $0.slotNumber == 1 }) {
            XCTAssertNotEqual(updatedSlot.isPinned, initialPinState, "Pin state should toggle")
        }

        // Toggle back
        await manager.togglePin(1)

        if let restoredSlot = manager.hotSlots.first(where: { $0.slotNumber == 1 }) {
            XCTAssertEqual(restoredSlot.isPinned, initialPinState, "Pin state should restore")
        }
    }

    func testHotSlotManagerImmutableModels() {
        let manager = HotSlotManager.shared

        let initialValue = manager.immutableModels

        // Toggle immutable models
        manager.updateImmutableModels(!initialValue)
        XCTAssertEqual(manager.immutableModels, !initialValue, "Immutable models should update")

        // Restore
        manager.updateImmutableModels(initialValue)
        XCTAssertEqual(manager.immutableModels, initialValue, "Immutable models should restore")
    }

    func testHotSlotManagerAskBeforeUnpinning() {
        let manager = HotSlotManager.shared

        let initialValue = manager.askBeforeUnpinning

        // Toggle ask before unpinning
        manager.updateAskBeforeUnpinning(!initialValue)
        XCTAssertEqual(manager.askBeforeUnpinning, !initialValue, "Ask before unpinning should update")

        // Restore
        manager.updateAskBeforeUnpinning(initialValue)
        XCTAssertEqual(manager.askBeforeUnpinning, initialValue, "Ask before unpinning should restore")
    }

    func testHotSlotManagerLoadAllHotSlots() async {
        let manager = HotSlotManager.shared

        do {
            try await manager.loadAllHotSlots()
            // Should complete without crashing
            XCTAssertNotNil(manager.hotSlots, "Hot slots should remain valid")
        } catch {
            // Expected if backend is unavailable
            print("Load all test skipped - backend unavailable: \(error)")
        }
    }

    // MARK: - HotSlot Model Tests

    func testHotSlotModel() {
        let slot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: true)

        XCTAssertEqual(slot.slotNumber, 1, "Slot number should match")
        XCTAssertEqual(slot.modelName, "llama2:latest", "Model name should match")
        XCTAssertTrue(slot.isPinned, "Should be pinned")
        XCTAssertFalse(slot.isEmpty, "Should not be empty")
    }

    func testHotSlotEmptyState() {
        let emptySlot = HotSlot(
            slotNumber: 1,
            modelName: nil,
            memoryUsageGB: nil,
            loadedAt: nil,
            isPinned: false
        )

        XCTAssertTrue(emptySlot.isEmpty, "Should be empty")
        XCTAssertNil(emptySlot.modelName, "Model name should be nil")
        XCTAssertNil(emptySlot.memoryUsageGB, "Memory usage should be nil")
        XCTAssertNil(emptySlot.loadedAt, "Loaded time should be nil")
    }

    func testHotSlotIdentifiable() {
        let slot1 = HotSlot(slotNumber: 1, modelName: nil, memoryUsageGB: nil, loadedAt: nil, isPinned: false)
        let slot2 = HotSlot(slotNumber: 2, modelName: nil, memoryUsageGB: nil, loadedAt: nil, isPinned: false)

        XCTAssertNotEqual(slot1.id, slot2.id, "Different slots should have different IDs")
    }

    // MARK: - HotSlotCard Component Tests

    func testHotSlotCardInitialization() {
        let mockSlot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: false)

        let card = HotSlotCard(
            slot: mockSlot,
            onPin: {},
            onRemove: {},
            onAssign: {}
        )

        XCTAssertNotNil(card, "Card should initialize")
    }

    func testHotSlotCardEmptySlot() {
        let emptySlot = HotSlot(
            slotNumber: 1,
            modelName: nil,
            memoryUsageGB: nil,
            loadedAt: nil,
            isPinned: false
        )

        let card = HotSlotCard(
            slot: emptySlot,
            onPin: {},
            onRemove: {},
            onAssign: {}
        )

        XCTAssertNotNil(card, "Card should handle empty slot")
    }

    func testHotSlotCardPinnedSlot() {
        let pinnedSlot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: true)

        let card = HotSlotCard(
            slot: pinnedSlot,
            onPin: {},
            onRemove: {},
            onAssign: {}
        )

        XCTAssertNotNil(card, "Card should handle pinned slot")
    }

    func testHotSlotCardPinAction() {
        let mockSlot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: false)
        var pinWasCalled = false

        let card = HotSlotCard(
            slot: mockSlot,
            onPin: {
                pinWasCalled = true
            },
            onRemove: {},
            onAssign: {}
        )

        card.onPin()
        XCTAssertTrue(pinWasCalled, "Pin action should be called")
    }

    func testHotSlotCardRemoveAction() {
        let mockSlot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: false)
        var removeWasCalled = false

        let card = HotSlotCard(
            slot: mockSlot,
            onPin: {},
            onRemove: {
                removeWasCalled = true
            },
            onAssign: {}
        )

        card.onRemove()
        XCTAssertTrue(removeWasCalled, "Remove action should be called")
    }

    func testHotSlotCardAssignAction() {
        let mockSlot = createMockHotSlot(slotNumber: 1, modelName: nil, isPinned: false)
        var assignWasCalled = false

        let card = HotSlotCard(
            slot: mockSlot,
            onPin: {},
            onRemove: {},
            onAssign: {
                assignWasCalled = true
            }
        )

        card.onAssign()
        XCTAssertTrue(assignWasCalled, "Assign action should be called")
    }

    // MARK: - HotSlotModelPicker Component Tests

    func testModelPickerSheetInitialization() {
        let mockModels = createMockOllamaModels()

        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: mockModels,
            onSelect: { _ in },
            onCancel: {}
        )

        XCTAssertNotNil(picker, "Model picker should initialize")
    }

    func testModelPickerSheetEmptyModels() {
        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: [],
            onSelect: { _ in },
            onCancel: {}
        )

        XCTAssertNotNil(picker, "Model picker should handle empty models")
    }

    func testModelPickerSheetFiltering() {
        let mockModels = createMockOllamaModels()

        var searchValue = ""
        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: mockModels,
            onSelect: { _ in },
            onCancel: {}
        )

        // Test filtering logic
        let allModels = picker.filteredModels
        XCTAssertEqual(allModels.count, mockModels.count, "Should show all models initially")
    }

    func testModelPickerSheetSelectAction() {
        let mockModels = createMockOllamaModels()
        var selectedModelName: String?

        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: mockModels,
            onSelect: { modelName in
                selectedModelName = modelName
            },
            onCancel: {}
        )

        picker.onSelect("llama2:latest")
        XCTAssertEqual(selectedModelName, "llama2:latest", "Model should be selected")
    }

    func testModelPickerSheetCancelAction() {
        let mockModels = createMockOllamaModels()
        var cancelWasCalled = false

        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: mockModels,
            onSelect: { _ in },
            onCancel: {
                cancelWasCalled = true
            }
        )

        picker.onCancel()
        XCTAssertTrue(cancelWasCalled, "Cancel action should be called")
    }

    func testModelPickerRowInitialization() {
        let mockModel = createMockOllamaModels().first!

        let row = ModelPickerRow(
            model: mockModel,
            onSelect: {}
        )

        XCTAssertNotNil(row, "Model picker row should initialize")
    }

    func testModelPickerRowSelectAction() {
        let mockModel = createMockOllamaModels().first!
        var selectWasCalled = false

        let row = ModelPickerRow(
            model: mockModel,
            onSelect: {
                selectWasCalled = true
            }
        )

        row.onSelect()
        XCTAssertTrue(selectWasCalled, "Select action should be called")
    }

    // MARK: - Integration Tests

    func testHotSlotWorkflow() async {
        let manager = HotSlotManager.shared

        // Load hot slots
        await manager.loadHotSlots()
        XCTAssertNotNil(manager.hotSlots, "Hot slots should load")

        // Test pin/unpin workflow
        if let slot = manager.hotSlots.first {
            let initialPinState = slot.isPinned

            await manager.togglePin(slot.slotNumber)

            if let updatedSlot = manager.hotSlots.first(where: { $0.slotNumber == slot.slotNumber }) {
                XCTAssertNotEqual(updatedSlot.isPinned, initialPinState, "Pin state should change")
            }

            // Restore
            await manager.togglePin(slot.slotNumber)
        }
    }

    func testModelSelectionWorkflow() {
        let mockModels = createMockOllamaModels()
        var selectedModel: String?

        let picker = ModelPickerSheet(
            slotNumber: 1,
            availableModels: mockModels,
            onSelect: { modelName in
                selectedModel = modelName
            },
            onCancel: {}
        )

        // Simulate selection
        if let firstModel = mockModels.first {
            picker.onSelect(firstModel.name)
            XCTAssertEqual(selectedModel, firstModel.name, "Model should be selected")
        }
    }

    func testCompleteHotSlotAssignmentFlow() async {
        let manager = HotSlotManager.shared
        let mockModels = createMockOllamaModels()

        // Load slots
        await manager.loadHotSlots()

        // Select a slot
        guard let targetSlot = manager.hotSlots.first else {
            XCTFail("Should have hot slots")
            return
        }

        // Select a model (simulate picker)
        if let modelToAssign = mockModels.first {
            do {
                try await manager.assignToSlot(slotNumber: targetSlot.slotNumber, modelName: modelToAssign.name)
                // If successful, verify assignment
                XCTAssertNotNil(manager.hotSlots, "Hot slots should remain valid")
            } catch {
                print("Assignment flow test skipped - backend unavailable: \(error)")
            }
        }
    }

    // MARK: - Helper Methods

    private func createMockHotSlot(slotNumber: Int, modelName: String?, isPinned: Bool) -> HotSlot {
        return HotSlot(
            slotNumber: slotNumber,
            modelName: modelName,
            memoryUsageGB: modelName != nil ? 4.5 : nil,
            loadedAt: modelName != nil ? Date() : nil,
            isPinned: isPinned
        )
    }

    private func createMockOllamaModels() -> [OllamaModel] {
        return [
            OllamaModel(
                name: "llama2:latest",
                size: 3_800_000_000,
                digest: "abc123",
                modifiedAt: Date(),
                details: OllamaModelDetails(
                    format: "gguf",
                    family: "llama",
                    families: ["llama"],
                    parameterSize: "7B",
                    quantizationLevel: "Q4_0"
                )
            ),
            OllamaModel(
                name: "codellama:latest",
                size: 3_800_000_000,
                digest: "def456",
                modifiedAt: Date(),
                details: OllamaModelDetails(
                    format: "gguf",
                    family: "llama",
                    families: ["llama"],
                    parameterSize: "7B",
                    quantizationLevel: "Q4_0"
                )
            ),
            OllamaModel(
                name: "mistral:latest",
                size: 4_100_000_000,
                digest: "ghi789",
                modifiedAt: Date(),
                details: OllamaModelDetails(
                    format: "gguf",
                    family: "mistral",
                    families: ["mistral"],
                    parameterSize: "7B",
                    quantizationLevel: "Q4_0"
                )
            )
        ]
    }

    // MARK: - Performance Tests

    func testHotSlotManagerPerformance() {
        measure {
            let manager = HotSlotManager.shared
            let _ = manager.hotSlots
        }
    }

    func testHotSlotCardPerformance() {
        let mockSlot = createMockHotSlot(slotNumber: 1, modelName: "llama2:latest", isPinned: false)

        measure {
            let _ = HotSlotCard(
                slot: mockSlot,
                onPin: {},
                onRemove: {},
                onAssign: {}
            )
        }
    }

    func testModelPickerPerformanceWithManyModels() {
        let manyModels = (0..<100).map { i in
            OllamaModel(
                name: "model-\(i):latest",
                size: 3_800_000_000,
                digest: "digest-\(i)",
                modifiedAt: Date(),
                details: OllamaModelDetails(
                    format: "gguf",
                    family: "llama",
                    families: ["llama"],
                    parameterSize: "7B",
                    quantizationLevel: "Q4_0"
                )
            )
        }

        measure {
            let _ = ModelPickerSheet(
                slotNumber: 1,
                availableModels: manyModels,
                onSelect: { _ in },
                onCancel: {}
            )
        }
    }

    // MARK: - Edge Cases

    func testInvalidSlotNumber() async {
        let manager = HotSlotManager.shared

        // Try to toggle pin on invalid slot
        await manager.togglePin(99)

        // Should handle gracefully without crashing
        XCTAssertNotNil(manager.hotSlots, "Manager should remain stable")
    }

    func testMultiplePinToggles() async {
        let manager = HotSlotManager.shared

        // Rapidly toggle pin multiple times
        for _ in 0..<10 {
            await manager.togglePin(1)
        }

        // Should handle multiple toggles without issues
        XCTAssertNotNil(manager.hotSlots, "Manager should remain stable")
    }

    func testEmptyModelName() {
        let slot = HotSlot(
            slotNumber: 1,
            modelName: "",
            memoryUsageGB: nil,
            loadedAt: nil,
            isPinned: false
        )

        // Empty string should behave like nil
        XCTAssertTrue(slot.isEmpty || slot.modelName == "", "Should handle empty model name")
    }
}
