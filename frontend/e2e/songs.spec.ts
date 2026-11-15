import { expect, test } from '@playwright/test'

import { mockApi, settings, song } from './fixtures'

test.describe('Songbook UI', () => {
  test('lists songs and opens a song', async ({ page }) => {
    await mockApi(page)
    await page.goto('/songs')

    const card = page.locator('.song-card')
    await expect(card).toHaveCount(1)
    await expect(card).toContainText(song.title)
    await expect(card).toContainText(song.artist)

    await card.click()
    await expect(page).toHaveURL(new RegExp(`/songs/${song.id}$`))
    await expect(page.locator('.song-title')).toHaveText(song.title)
  })

  test('renders chords above the lyrics', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)

    await expect(page.locator('.song-title')).toHaveText(song.title)
    await expect(page.locator('.song-artist')).toHaveText(song.artist)
    await expect(page.locator('.chord-row').first()).toContainText('G')
    await expect(page.locator('.lyric-row').first()).toContainText('Hello world')
    await expect(page.locator('.song-controls')).toBeVisible()

    const chordBox = await page.locator('.chord-row').first().boundingBox()
    const lyricBox = await page.locator('.lyric-row').first().boundingBox()
    expect(chordBox).not.toBeNull()
    expect(lyricBox).not.toBeNull()
    expect(chordBox!.y).toBeLessThan(lyricBox!.y)
  })

  test('print mode hides controls and the version footer', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)

    await page.emulateMedia({ media: 'print' })

    await expect(page.locator('.song-controls')).toBeHidden()
    await expect(page.locator('.detail-actions')).toBeHidden()
    await expect(page.locator('.version-info')).toBeHidden()

    const paddingBottom = await page
      .locator('.song-display')
      .evaluate((el) => getComputedStyle(el).paddingBottom)
    expect(paddingBottom).toBe('0px')
  })

  test('redirects unauthenticated visitors to login', async ({ page }) => {
    await mockApi(page, { authenticated: false })
    await page.goto('/songs')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.locator('h1')).toHaveText('Songbook')
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
  })

  test('redirects to login when the session expires', async ({ page }) => {
    await mockApi(page, { unauthorized: true, seedAuthOnce: true })
    await page.goto('/songs')

    await expect(page).toHaveURL(/\/login$/)
    const auth = await page.evaluate(() => localStorage.getItem('auth'))
    expect(auth).toBeNull()
  })

  test('shows an error instead of failing silently when save fails', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, async (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ status: 500, json: { detail: 'Save failed' } })
      }
      return route.fallback()
    })

    await page.goto(`/songs/${song.id}/edit`)
    await expect(page.locator('.edit-form')).toBeVisible()
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.locator('.notice.error')).toHaveText('Save failed')
  })

  test('logs out to the login page', async ({ page }) => {
    await mockApi(page)
    await page.goto('/songs')

    await page.getByRole('button', { name: 'Logout' }).click()
    await expect(page).toHaveURL(/\/login$/)
    const auth = await page.evaluate(() => localStorage.getItem('auth'))
    expect(auth).toBeNull()
  })

  test('creates a song and shows a success notice', async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/songs', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: song })
      }
      return route.fallback()
    })

    await page.goto('/songs/new')
    const inputs = page.locator('.edit-form input[type="text"]')
    await inputs.nth(0).fill('Test Song')
    await inputs.nth(1).fill('Test Artist')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page).toHaveURL(new RegExp(`/songs/${song.id}\\?created=1$`))
    await expect(page.locator('.notice.success')).toHaveText('Song created')
  })

  test('requests song PDFs with the auth token', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)

    const requestPromise = page.waitForRequest((req) =>
      req.url().includes(`/api/export/song/${song.id}/pdf`),
    )
    await page.getByRole('button', { name: 'PDF' }).click()
    const request = await requestPromise

    expect(request.headers()['authorization']).toBe('Bearer e2e-token')
  })

  test('keeps a chord inside a word aligned', async ({ page }) => {
    await mockApi(page)
    const body = [
      '{title: Test Song}',
      '{artist: Test Artist}',
      '{start_of_verse}',
      'bri[C]ght',
      '{end_of_verse}',
    ].join('\n')
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body } }),
    )

    await page.goto(`/songs/${song.id}`)
    await expect(page.locator('.lyric-row').first()).toHaveText('bright')
    const chordRow = await page.locator('.chord-row').first().textContent()
    expect(chordRow?.indexOf('C')).toBe(3)
  })

  test('print view switches between one and two columns', async ({ page }) => {
    await mockApi(page)
    const lines = Array.from(
      { length: 80 },
      (_, i) => `[Em]Line ${i} [Bm]with [D]several [A]chords [B7]here`,
    ).join('\n')
    const body = [
      '{title: Test Song}',
      '{artist: Test Artist}',
      '{start_of_verse}',
      lines,
      '{end_of_verse}',
    ].join('\n')
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body } }),
    )

    await page.goto(`/songs/${song.id}/print?columns=2`)
    await expect(page.locator('.song-title')).toHaveText('Test Song')
    await expect(page.locator('.song-controls')).toHaveCount(0)

    await page.emulateMedia({ media: 'print' })
    await expect(page.locator('.print-toolbar')).toBeHidden()
    expect(
      await page.locator('.song-body').evaluate((el) => getComputedStyle(el).columnCount),
    ).toBe('2')

    await page.emulateMedia({ media: 'screen' })
    await page.getByRole('button', { name: '1', exact: true }).click()
    await page.emulateMedia({ media: 'print' })
    expect(
      await page.locator('.song-body').evaluate((el) => getComputedStyle(el).columnCount),
    ).not.toBe('2')
  })

  test('direct print uses the saved column setting', async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/settings', (route) =>
      route.fulfill({ json: { ...settings, double_column: true } }),
    )

    await page.goto(`/songs/${song.id}/print`)
    await expect(page.locator('.song-title')).toHaveText(song.title)
    await page.emulateMedia({ media: 'print' })
    expect(
      await page.locator('.song-body').evaluate((el) => getComputedStyle(el).columnCount),
    ).toBe('2')
  })

  test('sends tag and alphabet filters to the API', async ({ page }) => {
    await mockApi(page)
    await page.goto('/songs')
    await expect(page.locator('.song-card')).toHaveCount(1)
    await expect(page.locator('.song-tags')).toContainText('difficulty: easy')

    const difficultyRequest = page.waitForRequest(
      (req) => req.url().includes('/api/songs?') && req.url().includes('difficulty=easy'),
    )
    await page.selectOption('.filter-select', 'easy')
    await difficultyRequest

    const letterRequest = page.waitForRequest(
      (req) => req.url().includes('/api/songs?') && req.url().includes('letter=A'),
    )
    await page.getByRole('button', { name: 'A', exact: true }).click()
    await letterRequest
  })

  test('paginates with limit and offset', async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/songs?*', (route) =>
      route.fulfill({ json: [song], headers: { 'X-Total-Count': '60' } }),
    )

    await page.goto('/songs')
    await expect(page.locator('.pagination')).toBeVisible()
    await expect(page.locator('.pagination')).toContainText('60 songs')

    const pageTwoRequest = page.waitForRequest(
      (req) => req.url().includes('/api/songs?') && req.url().includes('offset=25'),
    )
    await page.getByRole('button', { name: '2', exact: true }).click()
    await pageTwoRequest
    await expect(page.locator('.pagination button.active')).toHaveText('2')
  })
})
