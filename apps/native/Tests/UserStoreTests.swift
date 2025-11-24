//
//  UserStoreTests.swift
//  MagnetarStudio Tests
//
//  Unit tests for UserStore authentication logic.
//

import XCTest
@testable import MagnetarStudio

final class UserStoreTests: XCTestCase {
    var userStore: UserStore!

    override func setUp() {
        super.setUp()
        userStore = UserStore()
    }

    override func tearDown() {
        userStore = nil
        super.tearDown()
    }

    func testInitialState() {
        XCTAssertNil(userStore.user)
        XCTAssertFalse(userStore.isAuthenticated)
        XCTAssertFalse(userStore.isLoading)
        XCTAssertNil(userStore.error)
    }

    func testLoginSuccess() async throws {
        // This is a placeholder - will need mock API client
        // TODO: Implement after adding dependency injection
    }

    func testLogout() async {
        // Set up authenticated state
        userStore.isAuthenticated = true
        userStore.user = User(
            id: UUID(),
            username: "testuser",
            role: "member"
        )

        // Logout
        await userStore.logout()

        // Verify state cleared
        XCTAssertNil(userStore.user)
        XCTAssertFalse(userStore.isAuthenticated)
    }
}
