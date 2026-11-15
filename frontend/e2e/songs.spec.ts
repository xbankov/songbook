import { expect, test } from '@playwright/test'

import { mockApi, settings, song, songbook, version } from './fixtures'

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

  test('shows version history and restores a version', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)

    await page.getByRole('button', { name: 'History' }).click()
    await expect(page.locator('.history-row')).toContainText('v1')

    page.once('dialog', (dialog) => dialog.accept())
    const restoreRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songs/${song.id}/versions/1/restore`) &&
        req.method() === 'POST',
    )
    await page.locator('.history-row').getByRole('button', { name: 'Restore' }).click()
    await restoreRequest

    await expect(page.locator('.song-title')).toHaveText('Old Title')
  })

  test('marks a version favourite and forks it', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    await page.getByRole('button', { name: 'History' }).click()
    await expect(page.locator('.history-row')).toContainText('by Test User')

    const favoriteRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songs/${song.id}/versions/1/favorite`) &&
        req.method() === 'POST',
    )
    await page.locator('.history-row button[title="Favourite"]').click()
    await favoriteRequest
    await expect(
      page.locator('.history-row button[title="Remove favourite"]'),
    ).toBeVisible()

    const forkRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songs/${song.id}/versions/1/fork`) &&
        req.method() === 'POST',
    )
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByRole('button', { name: 'Fork' }).click()
    await forkRequest
    await expect(page).toHaveURL(/44444444-4444-4444-4444-444444444444/)
  })

  test('copies a version permalink', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    await page.getByRole('button', { name: 'History' }).click()

    await page.getByRole('button', { name: 'Link', exact: true }).click()
    await expect(page.locator('.notice.success')).toContainText('copied')

    const copied = await page.evaluate(() => navigator.clipboard.readText())
    expect(copied).toContain(`/songs/${song.id}/print?version=1`)
  })

  test('edits, reorders, and renames a songbook', async ({ page }) => {
    await mockApi(page)
    const firstEntry = songbook.entries[0]
    await page.goto(`/songbooks/${songbook.id}`)
    await expect(page.locator('.entry')).toHaveCount(2)

    await page.locator('.entry').first().click()
    await expect(page.locator('.song-display')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Scroll' })).toBeVisible()

    const transposeRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songbooks/${songbook.id}/songs/${firstEntry.id}`) &&
        req.method() === 'PUT' &&
        (req.postData() || '').includes('"transpose":1'),
    )
    await page.locator('.entry-controls button[title="Transpose up"]').first().click()
    await transposeRequest

    const columnsRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songbooks/${songbook.id}/songs/${firstEntry.id}`) &&
        req.method() === 'PUT' &&
        (req.postData() || '').includes('"double_column":1'),
    )
    await page.locator('.entry').first().locator('button[title="Toggle 2 columns"]').click()
    await columnsRequest

    const moveRequest = page.waitForRequest(
      (req) =>
        req.url().includes(`/api/songbooks/${songbook.id}/order`) &&
        req.method() === 'PUT' &&
        (req.postData() || '').includes(firstEntry.id),
    )
    await page.locator('.entry').first().locator('button[title="Move down"]').click()
    await moveRequest
    await expect(page.locator('.entry-title').first()).toHaveText('Second Song')

    await page.getByRole('button', { name: 'Edit' }).click()
    await page.locator('.edit-book input').first().fill('Renamed Book')
    const renameRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith(`/api/songbooks/${songbook.id}`) && req.method() === 'PUT',
    )
    await page.getByRole('button', { name: 'Save' }).click()
    await renameRequest
    await expect(page.locator('.header h1')).toHaveText('Renamed Book')
  })

  test('downloads ChordPro for a song and a songbook', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    const songDownload = page.waitForEvent('download')
    await page.getByRole('button', { name: 'ChordPro' }).click()
    expect((await songDownload).suggestedFilename()).toContain('.cho')

    await page.goto(`/songbooks/${songbook.id}`)
    const bookDownload = page.waitForEvent('download')
    await page.getByRole('button', { name: 'ChordPro' }).click()
    expect((await bookDownload).suggestedFilename()).toContain('.cho')
  })
})
