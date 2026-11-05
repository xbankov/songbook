import { test, expect } from '@playwright/test'

test.describe('Songbook App', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('shows the song list page', async ({ page }) => {
    await expect(page.locator('nav')).toContainText('Songbook')
    await expect(page).toHaveURL(/\/songs/)
  })

  test('can navigate to add song page', async ({ page }) => {
    await page.click('text=Add Song')
    await expect(page).toHaveURL(/\/songs\/new/)
    await expect(page.locator('h1')).toContainText('New Song')
  })

  test('can create a new song', async ({ page }) => {
    await page.click('text=Add Song')
    await page.fill('input[placeholder]', 'Test Song')
    await page.fill('input[type="text"]', 'Test Artist')
    await page.fill('textarea', '[C]Hello [G]world')
    await page.click('text=Save')
    await page.waitForTimeout(1000)
  })

  test('shows songbooks page', async ({ page }) => {
    await page.click('text=Songbooks')
    await expect(page).toHaveURL(/\/songbooks/)
    await expect(page.locator('h1')).toContainText('Songbooks')
  })

  test('can navigate to settings', async ({ page }) => {
    await page.click('text=Settings')
    await expect(page).toHaveURL(/\/settings/)
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('shows login page', async ({ page }) => {
    await page.click('text=Login')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h1')).toContainText('Login')
  })

  test('can register a new account', async ({ page }) => {
    await page.click('text=Login')
    await page.click('text=Register')
    await page.fill('input[type="text"]', 'testuser')
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    // Should redirect to songs after registration
    await page.waitForURL(/\/songs/)
  })
})
