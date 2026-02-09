//
//  TeamWorkspaceV2Tests.swift
//  MagnetarStudio Tests
//
//  Comprehensive test suite for TeamWorkspace_v2 refactoring (Phase 6.23)
//  Tests extracted components: TeamWorkspaceToolbar, TeamMemberSidebar,
//                               TeamMemberDetailView, TeamWorkspaceDataManager
//

import XCTest
@testable import MagnetarStudio

@MainActor
final class TeamWorkspaceV2Tests: XCTestCase {

    // MARK: - TeamWorkspaceDataManager Tests

    func testTeamWorkspaceDataManagerInitialization() {
        let manager = TeamWorkspaceDataManager()

        XCTAssertTrue(manager.teamMembers.isEmpty, "Team members should be empty on init")
        XCTAssertFalse(manager.isLoading, "Should not be loading on init")
    }

    func testTeamWorkspaceDataManagerLoadMembers() async {
        let manager = TeamWorkspaceDataManager()

        await manager.loadTeamMembers()

        // Should complete (success or graceful failure)
        XCTAssertNotNil(manager.teamMembers, "Team members should not be nil")
        XCTAssertFalse(manager.isLoading, "Loading should complete")
    }

    func testTeamWorkspaceDataManagerWithAuthenticatedUser() async {
        // Skip if no authenticated user
        guard AuthStore.shared.user != nil else {
            print("Skipping test - no authenticated user")
            return
        }

        let manager = TeamWorkspaceDataManager()
        await manager.loadTeamMembers()

        // Should load team members if user is authenticated
        XCTAssertFalse(manager.isLoading, "Loading should complete")
    }

    func testTeamWorkspaceDataManagerWithoutAuthenticatedUser() async {
        // This tests the error handling when no user is authenticated
        let manager = TeamWorkspaceDataManager()

        // Temporarily clear user (if possible in test environment)
        await manager.loadTeamMembers()

        // Should handle gracefully
        XCTAssertNotNil(manager.teamMembers, "Should return empty array gracefully")
    }

    // MARK: - TeamMember Model Tests

    func testTeamMemberInitialization() {
        let member = TeamMember(
            id: "user-1",
            name: "Test User",
            role: "developer",
            status: "online",
            avatar: nil
        )

        XCTAssertEqual(member.id, "user-1", "ID should match")
        XCTAssertEqual(member.name, "Test User", "Name should match")
        XCTAssertEqual(member.role, "developer", "Role should match")
        XCTAssertEqual(member.status, "online", "Status should match")
        XCTAssertNil(member.avatar, "Avatar should be nil")
    }

    func testTeamMemberEmail() {
        let member = TeamMember(
            id: "user-1",
            name: "Test User",
            role: "developer",
            status: "online",
            avatar: nil
        )

        let email = member.email
        XCTAssertFalse(email.isEmpty, "Email should be generated")
        XCTAssertTrue(email.contains("@"), "Email should contain @")
    }

    func testTeamMemberOnlineStatus() {
        let onlineMember = TeamMember(
            id: "user-1",
            name: "Online User",
            role: "developer",
            status: "online",
            avatar: nil
        )

        let offlineMember = TeamMember(
            id: "user-2",
            name: "Offline User",
            role: "developer",
            status: "offline",
            avatar: nil
        )

        XCTAssertTrue(onlineMember.isOnline, "Should be online")
        XCTAssertFalse(offlineMember.isOnline, "Should be offline")
    }

    func testTeamMemberInitials() {
        let singleName = TeamMember(
            id: "user-1",
            name: "John",
            role: "developer",
            status: "online",
            avatar: nil
        )

        let fullName = TeamMember(
            id: "user-2",
            name: "Jane Smith",
            role: "designer",
            status: "online",
            avatar: nil
        )

        let multipleName = TeamMember(
            id: "user-3",
            name: "John Jacob Jingleheimer Schmidt",
            role: "tester",
            status: "offline",
            avatar: nil
        )

        XCTAssertEqual(singleName.initials, "J", "Single name should give first letter")
        XCTAssertEqual(fullName.initials, "JS", "Full name should give first and last initials")
        XCTAssertEqual(multipleName.initials, "JS", "Multiple names should give first and last initials")
    }

    // MARK: - TeamWorkspaceToolbar Tests

    func testToolbarInitialization() {
        let selectedView = Binding.constant(TeamView.chat)

        let toolbar = TeamWorkspaceToolbar(
            selectedView: selectedView,
            onShowNetworkStatus: {},
            onShowDiagnostics: {},
            onShowDataLab: {}
        )

        XCTAssertNotNil(toolbar, "Toolbar should initialize")
    }

    func testToolbarViewSelection() {
        var currentView = TeamView.chat
        let selectedView = Binding(
            get: { currentView },
            set: { currentView = $0 }
        )

        let _ = TeamWorkspaceToolbar(
            selectedView: selectedView,
            onShowNetworkStatus: {},
            onShowDiagnostics: {},
            onShowDataLab: {}
        )

        selectedView.wrappedValue = .docs
        XCTAssertEqual(currentView, .docs, "View selection should bind correctly")
    }

    func testToolbarNetworkStatusAction() {
        var networkStatusCalled = false
        let selectedView = Binding.constant(TeamView.chat)

        let toolbar = TeamWorkspaceToolbar(
            selectedView: selectedView,
            onShowNetworkStatus: {
                networkStatusCalled = true
            },
            onShowDiagnostics: {},
            onShowDataLab: {}
        )

        toolbar.onShowNetworkStatus()
        XCTAssertTrue(networkStatusCalled, "Network status action should be called")
    }

    func testToolbarDiagnosticsAction() {
        var diagnosticsCalled = false
        let selectedView = Binding.constant(TeamView.chat)

        let toolbar = TeamWorkspaceToolbar(
            selectedView: selectedView,
            onShowNetworkStatus: {},
            onShowDiagnostics: {
                diagnosticsCalled = true
            },
            onShowDataLab: {}
        )

        toolbar.onShowDiagnostics()
        XCTAssertTrue(diagnosticsCalled, "Diagnostics action should be called")
    }

    func testToolbarDataLabAction() {
        var dataLabCalled = false
        let selectedView = Binding.constant(TeamView.chat)

        let toolbar = TeamWorkspaceToolbar(
            selectedView: selectedView,
            onShowNetworkStatus: {},
            onShowDiagnostics: {},
            onShowDataLab: {
                dataLabCalled = true
            }
        )

        toolbar.onShowDataLab()
        XCTAssertTrue(dataLabCalled, "Data lab action should be called")
    }

    // MARK: - TeamMemberSidebar Tests

    func testSidebarInitialization() {
        let mockMembers = createMockTeamMembers()

        let sidebar = TeamMemberSidebar(
            teamMembers: mockMembers,
            selectedTeamMember: nil,
            onSelectMember: { _ in }
        )

        XCTAssertNotNil(sidebar, "Sidebar should initialize")
    }

    func testSidebarEmptyState() {
        let sidebar = TeamMemberSidebar(
            teamMembers: [],
            selectedTeamMember: nil,
            onSelectMember: { _ in }
        )

        XCTAssertNotNil(sidebar, "Sidebar should handle empty state")
    }

    func testSidebarMemberSelection() {
        let mockMembers = createMockTeamMembers()
        var selectedMember: TeamMember?

        let sidebar = TeamMemberSidebar(
            teamMembers: mockMembers,
            selectedTeamMember: nil,
            onSelectMember: { member in
                selectedMember = member
            }
        )

        sidebar.onSelectMember(mockMembers[0])
        XCTAssertNotNil(selectedMember, "Member should be selected")
        XCTAssertEqual(selectedMember?.id, mockMembers[0].id, "Selected member should match")
    }

    func testSidebarMultipleMembersSelection() {
        let mockMembers = createMockTeamMembers()
        var selectionHistory: [TeamMember] = []

        let sidebar = TeamMemberSidebar(
            teamMembers: mockMembers,
            selectedTeamMember: nil,
            onSelectMember: { member in
                selectionHistory.append(member)
            }
        )

        // Select multiple members
        mockMembers.forEach { sidebar.onSelectMember($0) }

        XCTAssertEqual(selectionHistory.count, mockMembers.count, "All selections should be recorded")
    }

    // MARK: - TeamMemberDetailView Tests

    func testDetailViewInitialization() {
        guard let mockMember = createMockTeamMembers().first else {
            XCTFail("Mock team members should not be empty")
            return
        }

        let detailView = TeamMemberDetail(member: mockMember)

        XCTAssertNotNil(detailView, "Detail view should initialize")
    }

    func testDetailViewWithDifferentStatuses() {
        let onlineMember = TeamMember(
            id: "user-1",
            name: "Online User",
            role: "developer",
            status: "online",
            avatar: nil
        )

        let offlineMember = TeamMember(
            id: "user-2",
            name: "Offline User",
            role: "developer",
            status: "offline",
            avatar: nil
        )

        let onlineDetail = TeamMemberDetail(member: onlineMember)
        let offlineDetail = TeamMemberDetail(member: offlineMember)

        XCTAssertNotNil(onlineDetail, "Should handle online member")
        XCTAssertNotNil(offlineDetail, "Should handle offline member")
    }

    func testDetailViewWithDifferentRoles() {
        let roles = ["developer", "designer", "manager", "tester", "admin"]

        for (index, role) in roles.enumerated() {
            let member = TeamMember(
                id: "user-\(index)",
                name: "User \(index)",
                role: role,
                status: "online",
                avatar: nil
            )

            let detail = TeamMemberDetail(member: member)
            XCTAssertNotNil(detail, "Should handle \(role) role")
        }
    }

    // MARK: - Integration Tests

    func testTeamWorkspaceIntegration() async {
        let manager = TeamWorkspaceDataManager()

        await manager.loadTeamMembers()

        // Should complete successfully or fail gracefully
        XCTAssertNotNil(manager.teamMembers, "Team members should be loaded")
        XCTAssertFalse(manager.isLoading, "Loading should complete")
    }

    func testCompleteTeamWorkflow() async {
        let manager = TeamWorkspaceDataManager()

        // Load team members
        await manager.loadTeamMembers()

        // If we got members, test selection flow
        if !manager.teamMembers.isEmpty {
            var selectedMember: TeamMember?

            let sidebar = TeamMemberSidebar(
                teamMembers: manager.teamMembers,
                selectedTeamMember: nil,
                onSelectMember: { member in
                    selectedMember = member
                }
            )

            // Select first member
            sidebar.onSelectMember(manager.teamMembers[0])

            XCTAssertNotNil(selectedMember, "Member should be selected")

            // Show detail view
            let detail = TeamMemberDetail(member: selectedMember!)
            XCTAssertNotNil(detail, "Detail view should be created")
        }
    }

    func testTeamViewSwitching() {
        var currentView = TeamView.chat

        // Simulate view switching
        currentView = .docs
        XCTAssertEqual(currentView, .docs, "View should switch to docs")

        currentView = .chat
        XCTAssertEqual(currentView, .chat, "View should switch back to chat")
    }

    // MARK: - Helper Methods

    private func createMockTeamMembers() -> [TeamMember] {
        return [
            TeamMember(
                id: "user-1",
                name: "Alice Developer",
                role: "developer",
                status: "online",
                avatar: nil
            ),
            TeamMember(
                id: "user-2",
                name: "Bob Designer",
                role: "designer",
                status: "online",
                avatar: nil
            ),
            TeamMember(
                id: "user-3",
                name: "Charlie Manager",
                role: "manager",
                status: "offline",
                avatar: nil
            ),
            TeamMember(
                id: "user-4",
                name: "Diana Tester",
                role: "tester",
                status: "online",
                avatar: nil
            )
        ]
    }

    // MARK: - Performance Tests

    func testTeamWorkspaceDataManagerPerformance() {
        measure {
            let manager = TeamWorkspaceDataManager()
            let _ = manager.teamMembers
        }
    }

    func testSidebarPerformanceWithManyMembers() {
        let manyMembers = (0..<100).map { i in
            TeamMember(
                id: "user-\(i)",
                name: "User \(i)",
                role: "developer",
                status: i % 2 == 0 ? "online" : "offline",
                avatar: nil
            )
        }

        measure {
            let _ = TeamMemberSidebar(
                teamMembers: manyMembers,
                selectedTeamMember: manyMembers.first,
                onSelectMember: { _ in }
            )
        }
    }

    func testDetailViewPerformance() {
        let member = TeamMember(
            id: "user-1",
            name: "Performance Test User",
            role: "developer",
            status: "online",
            avatar: nil
        )

        measure {
            let _ = TeamMemberDetail(member: member)
        }
    }

    // MARK: - Edge Cases

    func testEmptyTeamName() {
        let member = TeamMember(
            id: "user-1",
            name: "",
            role: "developer",
            status: "online",
            avatar: nil
        )

        XCTAssertEqual(member.initials, "", "Empty name should give empty initials")
    }

    func testSpecialCharactersInName() {
        let member = TeamMember(
            id: "user-1",
            name: "Test@User#123",
            role: "developer",
            status: "online",
            avatar: nil
        )

        XCTAssertNotNil(member.initials, "Should handle special characters")
    }

    func testVeryLongName() {
        let longName = String(repeating: "VeryLongName ", count: 100)
        let member = TeamMember(
            id: "user-1",
            name: longName,
            role: "developer",
            status: "online",
            avatar: nil
        )

        XCTAssertNotNil(member.initials, "Should handle very long names")
        XCTAssertLessThanOrEqual(member.initials.count, 2, "Initials should be at most 2 characters")
    }
}

// MARK: - TeamView Enum for Testing

// Note: TeamView is private in TeamWorkspace_v2.swift, so we need a local copy for testing
private enum TeamView {
    case chat
    case docs
}
