import { test, expect } from '@playwright/test'

/**
 * E2E Smoke Tests for Code Tab
 *
 * Prerequisites:
 * - Backend server running at http://localhost:8000
 * - Frontend server running at http://localhost:4200
 * - Valid auth session (login before running tests)
 *
 * Test Scenarios:
 * 1. Diff-confirm flow: Open file → Edit → Save → Review diff → Confirm
 * 2. 409 Conflict: Simulate concurrent edit with conflict warning
 */

test.describe('Code Tab - Diff Confirm Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Check if servers are reachable
    const response = await page.goto('/')
    if (!response || !response.ok()) {
      test.skip('Frontend server not reachable - skipping E2E tests')
    }

    // Navigate to Code Tab
    await page.goto('/code')
    await page.waitForLoadState('networkidle')
  })

  test('should open file, edit, save with diff modal, and confirm', async ({ page }) => {
    test.setTimeout(60000) // 60 second timeout for full flow

    // Step 1: Check if workspace is loaded (may require manual setup)
    const fileTree = page.locator('[data-testid="file-tree"]').first()
    const hasFiles = await fileTree.count() > 0

    if (!hasFiles) {
      console.log('No workspace loaded - test requires workspace setup')
      test.skip('Workspace not loaded - manual setup required')
    }

    // Step 2: Open first file in tree
    const firstFile = page.locator('[data-testid="file-item"]').first()
    await firstFile.click()
    await page.waitForTimeout(1000) // Wait for file to load

    // Step 3: Enter edit mode
    const editButton = page.locator('button:has-text("Edit")').first()
    if (await editButton.count() > 0) {
      await editButton.click()
    }

    // Step 4: Make a change in Monaco editor
    // Monaco requires special handling - send keyboard input to editor
    const editorTextarea = page.locator('textarea.inputarea').first()
    await editorTextarea.focus()
    await editorTextarea.press('End') // Go to end of line
    await editorTextarea.type('\n// E2E test comment')

    // Step 5: Trigger save (Cmd/Ctrl+S or click Save button)
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+s' : 'Control+s')
    await page.waitForTimeout(500)

    // Step 6: Verify diff modal appears
    const diffModal = page.locator('[data-testid="diff-confirm-modal"]').or(
      page.locator('text=Review Changes')
    )
    await expect(diffModal).toBeVisible({ timeout: 5000 })

    // Step 7: Verify diff content shows the change
    const diffPreview = page.locator('pre').filter({ hasText: 'E2E test comment' })
    await expect(diffPreview).toBeVisible()

    // Step 8: Confirm save
    const confirmButton = page.locator('button:has-text("Confirm")').or(
      page.locator('button:has-text("Confirm Save")')
    )
    await confirmButton.click()

    // Step 9: Verify success toast
    await expect(page.locator('text=/Saved|Success/i')).toBeVisible({ timeout: 5000 })
  })

  test('should show conflict warning on concurrent edit (409)', async ({ page, context }) => {
    test.setTimeout(90000) // 90 second timeout

    // This test requires two browser contexts to simulate concurrent editing
    const page2 = await context.newPage()

    try {
      // Step 1: Both pages navigate to Code Tab
      await page.goto('/code')
      await page2.goto('/code')
      await page.waitForLoadState('networkidle')
      await page2.waitForLoadState('networkidle')

      // Step 2: Check if workspace is loaded
      const fileTree = page.locator('[data-testid="file-tree"]').first()
      const hasFiles = await fileTree.count() > 0

      if (!hasFiles) {
        test.skip('Workspace not loaded - manual setup required')
      }

      // Step 3: Open same file in both tabs
      const firstFile = page.locator('[data-testid="file-item"]').first()
      const firstFile2 = page2.locator('[data-testid="file-item"]').first()
      await firstFile.click()
      await firstFile2.click()
      await page.waitForTimeout(1000)
      await page2.waitForTimeout(1000)

      // Step 4: Edit in both tabs
      const editorTextarea1 = page.locator('textarea.inputarea').first()
      const editorTextarea2 = page2.locator('textarea.inputarea').first()

      await editorTextarea1.focus()
      await editorTextarea1.press('End')
      await editorTextarea1.type('\n// Edit from tab 1')

      await editorTextarea2.focus()
      await editorTextarea2.press('End')
      await editorTextarea2.type('\n// Edit from tab 2')

      // Step 5: Save in first tab (succeeds)
      await page.keyboard.press(process.platform === 'darwin' ? 'Meta+s' : 'Control+s')
      await page.waitForTimeout(500)

      const diffModal1 = page.locator('text=Review Changes')
      await expect(diffModal1).toBeVisible({ timeout: 5000 })

      const confirmButton1 = page.locator('button:has-text("Confirm Save")').first()
      await confirmButton1.click()

      await expect(page.locator('text=/Saved|Success/i')).toBeVisible({ timeout: 5000 })

      // Step 6: Save in second tab (should show conflict)
      await page2.keyboard.press(process.platform === 'darwin' ? 'Meta+s' : 'Control+s')
      await page2.waitForTimeout(500)

      const diffModal2 = page2.locator('text=Review Changes')
      await expect(diffModal2).toBeVisible({ timeout: 5000 })

      const confirmButton2 = page2.locator('button:has-text("Confirm Save")').first()
      await confirmButton2.click()

      // Step 7: Verify conflict handling
      // Should either show error toast or re-open modal with conflict warning
      const conflictIndicator = page2.locator('text=/conflict|modified|409/i').first()
      await expect(conflictIndicator).toBeVisible({ timeout: 10000 })

      // Step 8: Verify diff modal shows conflict warning (orange banner)
      const conflictWarning = page2.locator('text=⚠️').or(
        page2.locator('text=/File changed|current:/i')
      )
      await expect(conflictWarning).toBeVisible()

    } finally {
      await page2.close()
    }
  })

  test('should toggle terminal with Cmd+/', async ({ page }) => {
    test.setTimeout(30000)

    // Navigate to Code Tab
    await page.goto('/code')
    await page.waitForLoadState('networkidle')

    // Terminal should be hidden initially
    const terminal = page.locator('text=Terminal').first()
    await expect(terminal).not.toBeVisible()

    // Press Cmd+/ (or Ctrl+/ on Windows/Linux)
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+/' : 'Control+/')
    await page.waitForTimeout(500)

    // Terminal should now be visible
    await expect(terminal).toBeVisible({ timeout: 5000 })

    // Press again to toggle off
    await page.keyboard.press(process.platform === 'darwin' ? 'Meta+/' : 'Control+/')
    await page.waitForTimeout(500)

    // Terminal should be hidden again
    await expect(terminal).not.toBeVisible()
  })
})

test.describe('Code Tab - Accessibility', () => {
  test('should have no automatic accessibility violations', async ({ page }) => {
    await page.goto('/code')
    await page.waitForLoadState('networkidle')

    // Basic accessibility checks
    await expect(page).toHaveTitle(/ElohimOS|Code/i)

    // Check for keyboard navigation
    await page.keyboard.press('Tab')
    await expect(page.locator(':focus')).toBeVisible()
  })
})
