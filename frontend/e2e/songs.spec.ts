import { expect, test } from '@playwright/test'

import { mockApi, settings, song, song2, songbook, version } from './fixtures'

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
    const chordRow = await page.locator('.chord-row').first().textContent()
    expect(chordRow?.indexOf('C')).toBe(6)
    await expect(page.locator('.lyric-row').first()).toContainText('Hello world')
    await expect(page.locator('.song-controls')).toBeVisible()

    const chordBox = await page.locator('.chord-row').first().boundingBox()
    const lyricBox = await page.locator('.lyric-row').first().boundingBox()
    expect(chordBox).not.toBeNull()
    expect(lyricBox).not.toBeNull()
    expect(chordBox!.y).toBeLessThan(lyricBox!.y)
  })

  test('opens and closes a chord reference in above, inline and performance modes', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    const dialog = page.getByRole('dialog', { name: 'Chord reference' })

    const aboveChord = page.getByRole('button', { name: 'G', exact: true }).first()
    await aboveChord.focus()
    await page.keyboard.press('Enter')
    await expect(dialog).toBeVisible()
    await expect(dialog).toBeFocused()
    await expect(dialog).toContainText('G')
    await expect(dialog.locator('.chord-diagram')).toBeVisible()
    await dialog.getByRole('button', { name: 'G7' }).click()
    await expect(dialog).toContainText('G7')
    await expect(dialog.locator('.chord-diagram')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)

    await page.getByRole('button', { name: 'Inline' }).click()
    await page.getByRole('button', { name: 'G', exact: true }).first().click()
    await expect(dialog).toBeVisible()
    await page.locator('.song-title').click()
    await expect(dialog).toHaveCount(0)

    // The same component and popover work in performance mode; Escape closes
    // the chord before it would exit performance mode.
    await page.getByRole('button', { name: 'Performance' }).click()
    await expect(page.locator('.play-stage')).toBeVisible()
    await page.getByRole('button', { name: 'G', exact: true }).first().click()
    await expect(dialog).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page).toHaveURL(`/songs/${song.id}?performance=1`)
  })

  test('adjacent chords keep separate clickable columns', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body: '[G][C]Hello' } }),
    )
    await page.goto(`/songs/${song.id}`)

    const buttons = page.locator('.chord-row .chord-above-btn')
    await expect(buttons).toHaveCount(2)
    const first = await buttons.nth(0).boundingBox()
    const second = await buttons.nth(1).boundingBox()
    expect(first).not.toBeNull()
    expect(second).not.toBeNull()
    expect(second!.x).toBeGreaterThan(first!.x)

    await buttons.nth(1).click()
    await expect(page.getByRole('dialog', { name: 'Chord reference' })).toContainText('C')
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

  test('explains when a site blocks URL import', async ({ page }) => {
    const detail =
      'Supermusic blocks automatic import: its song pages need a browser check first. ' +
      'Open the song in your browser, copy the text, and paste it into a new song or Bulk import.'
    await mockApi(page)
    await page.route('**/api/songs/import?*', (route) =>
      route.fulfill({ status: 400, json: { detail } }),
    )

    await page.goto('/songs')
    await page.getByRole('button', { name: 'Import URL' }).click()
    await page.getByPlaceholder(/supermusic/).fill('https://supermusic.cz/piesen.php?id=1')
    await page.getByRole('button', { name: 'Import Song' }).click()

    await expect(page.locator('.notice.error')).toContainText(/blocks automatic import.*paste/)
    await expect(page).toHaveURL(/\/songs$/)
  })

  test('previews uploaded files and imports only the chosen songs', async ({ page }) => {
    await mockApi(page)
    const entries = [
      { index: 0, filename: 'upload-new.txt', title: 'Wagon Wheel', artist: 'Unknown', capo: 0, key: null, duplicate: false, error: null },
      { index: 1, filename: 'upload-duplicate.cho', title: 'Test Song', artist: 'Test Artist', capo: 0, key: null, duplicate: true, error: null },
      { index: 2, filename: 'upload-broken.doc', title: 'broken', artist: 'Unknown', capo: 0, key: null, duplicate: false, error: 'Unsupported file type .doc' },
    ]
    let selected = ''
    await page.route('**/api/songs/import/files?*', (route) => {
      const url = new URL(route.request().url())
      if (url.searchParams.get('dry_run') === 'true') {
        return route.fulfill({ json: { entries } })
      }
      selected = url.searchParams.get('selected') ?? ''
      return route.fulfill({ status: 201, json: { imported: [song], skipped: [] } })
    })

    await page.goto('/songs')
    await page.getByRole('button', { name: 'Bulk', exact: true }).click()
    await page.locator('.batch-file-input').setInputFiles([
      'e2e/uploads/upload-new.txt',
      'e2e/uploads/upload-duplicate.cho',
      'e2e/uploads/upload-broken.doc',
    ])

    const rows = page.locator('.batch-table tbody tr')
    await expect(rows).toHaveCount(3)
    // A new song is selected; a duplicate is not; a broken file cannot be.
    await expect(rows.nth(0).locator('input[type="checkbox"]')).toBeChecked()
    await expect(rows.nth(1).locator('input[type="checkbox"]')).not.toBeChecked()
    await expect(rows.nth(1)).toContainText('duplicate')
    await expect(rows.nth(2).locator('.batch-error')).toHaveText(
      'Unsupported file type .doc',
    )
    await expect(rows.nth(2).locator('input[type="checkbox"]')).toBeDisabled()

    await page.getByRole('button', { name: 'Import 1 song' }).click()

    await expect(page.locator('.notice.success')).toHaveText('Imported 1 song')
    expect(selected).toBe('0')
  })

  test('distinguishes search results and imports the chosen one', async ({ page }) => {
    const tabUrl = 'https://tabs.ultimate-guitar.com/tab/misc-traditional/song-chords-1'
    const newestUrl = 'https://tabs.ultimate-guitar.com/tab/misc-traditional/song-chords-2'
    await mockApi(page)
    await page.route('**/api/search?*', (route) =>
      route.fulfill({
        json: {
          query: 'song',
          results: [
            {
              title: 'Song',
              artist: 'Trad',
              url: tabUrl,
              source: 'ultimate-guitar',
              type: 'Chords',
              type_label: 'Chords',
              rating: 4.8,
              votes: 1000,
              version: 3,
              version_count: 8,
              key: 'G',
              difficulty: 'intermediate',
              updated: '2024-03-01',
              verified: true,
            },
            {
              title: 'Song',
              artist: 'Trad',
              url: newestUrl,
              source: 'ultimate-guitar',
              type: 'Chords',
              type_label: 'Chords',
              rating: 4.5,
              votes: 10,
              version: 1,
              version_count: 2,
              key: 'A',
              difficulty: 'advanced',
              updated: '2025-02-01',
              verified: false,
            },
            {
              title: 'Song',
              artist: 'Trad',
              url: 'https://tabs.ultimate-guitar.com/tab/misc-traditional/song-tabs-3',
              source: 'ultimate-guitar',
              type: 'Tabs',
              type_label: 'Tabs',
              rating: 4.2,
              votes: 200,
              version: 2,
              version_count: 3,
              key: 'C',
              difficulty: 'novice',
              updated: '2023-01-01',
              verified: false,
            },
          ],
        },
      }),
    )
    let importedUrl = ''
    await page.route('**/api/songs/import?*', (route) => {
      importedUrl = new URL(route.request().url()).searchParams.get('url') ?? ''
      return route.fulfill({ status: 201, json: song })
    })

    await page.goto('/songs')
    await page.getByRole('button', { name: 'Search', exact: true }).click()
    await page.getByPlaceholder('Search for songs to import...').fill('song')
    await page.getByRole('button', { name: 'Search', exact: true }).last().click()
    const rows = page.locator('.search-result')
    await expect(rows).toHaveCount(3)
    const first = rows.first()
    await expect(first).toContainText('Best')
    await expect(first).toContainText('Chords')
    await expect(first).toContainText('v3 of 8')
    await expect(first).toContainText('4.8★ (1,000 votes)')
    await expect(first).toContainText('Key G')
    await expect(first).toContainText('intermediate')
    await expect(first).toContainText('updated 2024')
    await expect(first).toContainText('verified')
    await expect(first.getByRole('link', { name: 'Source: Ultimate Guitar' })).toHaveAttribute(
      'href',
      tabUrl,
    )

    // Most votes keeps the first row; Newest swaps the 2025 version first.
    await page.getByLabel('Sort search results').selectOption('votes')
    await expect(rows.first()).toContainText('v3 of 8')
    await page.getByLabel('Sort search results').selectOption('newest')
    await expect(rows.first()).toContainText('v1 of 2')
    await page.getByLabel('Sort search results').selectOption('best')
    await expect(rows.first()).toContainText('v3 of 8')

    await first.getByRole('button', { name: 'Import' }).click()

    await expect(page).toHaveURL(new RegExp(`/songs/${song.id}\\?imported=1$`))
    expect(importedUrl).toBe(tabUrl)
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

  test('shows the title and artist from the song fields', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({
        json: { ...song, title: 'Renamed Song', artist: 'Renamed Artist' },
      }),
    )

    await page.goto(`/songs/${song.id}`)
    await expect(page.locator('.song-title')).toHaveText('Renamed Song')
    await expect(page.locator('.song-artist')).toHaveText('Renamed Artist')
  })

  test('shows what the server stored after saving', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, async (route) => {
      if (route.request().method() === 'PUT') {
        // The server strips header tags and fills the empty key from them.
        return route.fulfill({ json: { ...song, key: 'D', body: '[D]Stored line' } })
      }
      return route.fallback()
    })

    await page.goto(`/songs/${song.id}/edit`)
    const editor = page.locator('.editor-textarea')
    const keyInput = page.locator('input[placeholder="e.g. G, Am"]')
    await keyInput.fill('')
    await editor.fill('{key: D}\n[D]Stored line')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(editor).toHaveValue('[D]Stored line')
    await expect(keyInput).toHaveValue('D')
  })

  test('keeps text typed while a save is in flight and saves it before transposing', async ({ page }) => {
    await mockApi(page)
    const puts: string[] = []
    let release!: () => void
    const held = new Promise<void>((resolve) => (release = resolve))
    await page.route(`**/api/songs/${song.id}`, async (route) => {
      if (route.request().method() === 'PUT') {
        const sent = route.request().postDataJSON()
        puts.push(sent.body)
        if (puts.length === 1) await held
        return route.fulfill({ json: { ...song, ...sent } })
      }
      return route.fallback()
    })
    await page.route(`**/api/songs/${song.id}/transpose**`, (route) =>
      route.fulfill({ json: { ...song, key: 'G#', body: '[G#]Typed during save' } }),
    )

    await page.goto(`/songs/${song.id}/edit`)
    const editor = page.locator('.editor-textarea')
    await editor.fill('[G]First draft')
    await page.getByRole('button', { name: 'Save' }).click()
    await editor.fill('[G]Typed during save')
    release()
    await expect(page.locator('.notice.success')).toHaveText('Saved')
    await expect(editor).toHaveValue('[G]Typed during save')

    // The text typed during the first save is still unsaved, so transposing
    // saves it first instead of replacing it with the server's older body.
    await page.getByRole('button', { name: '+1' }).click()
    await expect(editor).toHaveValue('[G#]Typed during save')
    expect(puts).toEqual(['[G]First draft', '[G]Typed during save'])
  })

  test('saves unsaved edits before transposing in the editor', async ({ page }) => {
    await mockApi(page)
    const calls: string[] = []
    let saved: Record<string, unknown> | null = null
    await page.route(`**/api/songs/${song.id}`, async (route) => {
      if (route.request().method() === 'PUT') {
        calls.push('save')
        saved = route.request().postDataJSON()
        return route.fulfill({ json: { ...song, ...saved } })
      }
      return route.fallback()
    })
    await page.route(`**/api/songs/${song.id}/transpose**`, (route) => {
      calls.push('transpose')
      return route.fulfill({
        json: { ...song, key: 'G#', body: '[G#]Edited [C#]line' },
      })
    })

    await page.goto(`/songs/${song.id}/edit`)
    const editor = page.locator('.editor-textarea')
    await expect(editor).toHaveValue(/\[G\]Hello/)
    await editor.fill('[G]Edited [C]line')
    await page.getByRole('button', { name: '+1' }).click()

    await expect(editor).toHaveValue('[G#]Edited [C#]line')
    expect(calls).toEqual(['save', 'transpose'])
    expect(saved!.body).toBe('[G]Edited [C]line')
    await expect(page.locator('.edit-form input[placeholder="e.g. G, Am"]')).toHaveValue('G#')

    // Nothing unsaved now, so the next transpose does not save again.
    await page.getByRole('button', { name: '+1' }).click()
    await expect.poll(() => calls.length).toBe(3)
    expect(calls[2]).toBe('transpose')
  })

  test('new song preview shows placeholders until the fields are filled', async ({ page }) => {
    await mockApi(page)
    await page.goto('/songs/new')
    await page.locator('.editor-textarea').fill('[G]Hello')

    await expect(page.locator('.preview .song-title')).toHaveText('Preview')
    await expect(page.locator('.preview .song-artist')).toHaveText('Artist')
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

  test('print view uses chords above even when inline is saved', async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/settings', (route) =>
      route.fulfill({ json: { ...settings, display_mode: 'inline' } }),
    )

    await page.goto(`/songs/${song.id}/print`)
    await expect(page.locator('.song-title')).toHaveText(song.title)
    await expect(page.locator('.section-label').first()).toContainText('Verse')
    await expect(page.locator('.chord-row').first()).toContainText('G')
    await expect(page.locator('.lyric-row').first()).toHaveText('Hello world')
    const chordBox = await page.locator('.chord-row').first().boundingBox()
    const lyricBox = await page.locator('.lyric-row').first().boundingBox()
    expect(chordBox).not.toBeNull()
    expect(lyricBox).not.toBeNull()
    expect(chordBox!.y).toBeLessThan(lyricBox!.y)
  })

  test('browser print uses tighter page margins', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    await page.emulateMedia({ media: 'print' })

    const margin = await page.evaluate(() => {
      const walk = (rules: CSSRuleList): string => {
        for (const rule of Array.from(rules)) {
          if (rule.constructor.name === 'CSSPageRule') {
            return (rule as CSSPageRule).style.margin
          }
          const nested = (rule as CSSGroupingRule).cssRules
          if (nested) {
            const found = walk(nested)
            if (found) return found
          }
        }
        return ''
      }
      for (const sheet of Array.from(document.styleSheets)) {
        try {
          const found = walk(sheet.cssRules)
          if (found) return found
        } catch {}
      }
      return ''
    })

    expect(margin).toContain('1.2cm')
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

  test('adds a YouTube link and loads the player only on request', async ({ page }) => {
    await mockApi(page)
    const canonical = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    const saved: (string | null)[] = []
    await page.route(`**/api/songs/${song.id}/youtube`, async (route) => {
      const { url } = route.request().postDataJSON() as { url: string | null }
      saved.push(url)
      const metadata = url ? { youtube_url: canonical } : {}
      await route.fulfill({ json: { ...song, metadata } })
    })
    let playerRequests = 0
    await page.route('https://www.youtube-nocookie.com/**', (route) => {
      playerRequests += 1
      return route.fulfill({ contentType: 'text/html', body: '<html></html>' })
    })

    await page.goto(`/songs/${song.id}`)
    await page.getByRole('button', { name: 'Add YouTube link' }).click()
    await page.getByLabel('YouTube link').fill('https://youtu.be/dQw4w9WgXcQ')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByRole('link', { name: 'Open on YouTube' })).toHaveAttribute('href', canonical)
    expect(saved).toEqual(['https://youtu.be/dQw4w9WgXcQ'])
    await expect(page.locator('.youtube-player iframe')).toHaveCount(0)
    expect(playerRequests).toBe(0)

    await page.getByRole('button', { name: 'Show video' }).click()
    await expect(page.locator('.youtube-player iframe')).toHaveAttribute(
      'src',
      'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ',
    )

    await page.getByRole('button', { name: 'Remove YouTube link' }).click()
    await expect(page.getByRole('button', { name: 'Add YouTube link' })).toBeVisible()
    expect(saved).toEqual(['https://youtu.be/dQw4w9WgXcQ', null])
  })

  test('edits songbook metadata without a chord chart', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songbooks/${songbook.id}`)
    await expect(page.locator('.book-meta')).toContainText('Author: Jane')
    await expect(page.locator('.chord-chart')).toHaveCount(0)

    await page.getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByLabel('Chord diagrams')).toHaveCount(0)
    await page.getByLabel('Genre').fill('bluegrass')
    await page.getByLabel('Date').fill('2026-05-01')
    const saveRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith(`/api/songbooks/${songbook.id}`) && req.method() === 'PUT',
    )
    await page.getByRole('button', { name: 'Save' }).click()
    const body = (await saveRequest).postDataJSON()
    expect(body).toEqual({ date: '2026-05-01', genre: 'bluegrass' })

    await expect(page.locator('.book-meta')).toContainText('Genre: bluegrass')
    await expect(page.locator('.book-meta')).toContainText('Date: 2026-05-01')
    // The chart stays gone even for a songbook that stored a chart mode.
    await expect(page.locator('.chord-chart')).toHaveCount(0)
  })

  test('opens the suggested-key analysis, closes it, and applies the key', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}/analyze`, (route) =>
      route.fulfill({
        json: {
          suggested_key: 'A',
          confidence: 82.5,
          method: 'diatonic chord match',
          key_type: 'major',
          chord_count: 11,
          key_chords: ['A', 'D', 'E', 'F#m', 'Bm', 'C#m'],
          chords: [
            { name: 'A', count: 5, in_key: true },
            { name: 'D', count: 3, in_key: true },
            { name: 'E', count: 2, in_key: true },
            { name: 'G', count: 1, in_key: false },
          ],
        },
      }),
    )
    await page.route(`**/api/songs/${song.id}`, (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ json: { ...song, key: 'A', version: 2 } })
      }
      return route.fulfill({ json: song })
    })

    await page.goto(`/songs/${song.id}`)
    const toggle = page.getByRole('button', { name: /Suggested key: A/ })
    const panel = page.getByRole('dialog', { name: 'Suggested key details' })
    await expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-expanded', 'true')
    await expect(panel).toContainText('A · major · 82.5% confidence')
    await expect(panel).toContainText('10 of 11 chord occurrences belong to this key')
    await expect(panel).toContainText('A×5')
    await expect(panel).toContainText('outside')

    // Outside click closes it.
    await page.locator('.song-title').click()
    await expect(panel).toHaveCount(0)

    // Escape closes it; Cancel leaves the song untouched.
    await toggle.click()
    await expect(panel).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(panel).toHaveCount(0)
    await toggle.click()
    await panel.getByRole('button', { name: 'Cancel' }).click()
    await expect(panel).toHaveCount(0)

    await toggle.click()
    const saveRequest = page.waitForRequest(
      (req) => req.url().endsWith(`/api/songs/${song.id}`) && req.method() === 'PUT',
    )
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Use A as the song key?')
      await dialog.accept()
    })
    await panel.getByRole('button', { name: 'Use as song key' }).click()
    expect((await saveRequest).postDataJSON()).toEqual({ key: 'A' })

    await expect(panel).toHaveCount(0)
    await expect(page.locator('.song-meta')).toContainText('Key: A')
    await expect(page.locator('.notice.success')).toContainText('Song key set to A (version 2)')
  })

  test('performance mode highlights the current line and follows keys and taps', async ({ page }) => {
    await mockApi(page)
    await page.goto(`/songs/${song.id}`)
    await page.getByRole('button', { name: 'Performance' }).click()
    await expect(page).toHaveURL(`/songs/${song.id}?performance=1`)

    // Full-screen stage: the app nav bar is covered.
    await expect(page.locator('.play-stage')).toBeVisible()
    await expect(page.locator('.active-line')).toHaveCount(1)
    await expect(page.locator('.active-line')).toHaveAttribute('data-line', '0')

    // The fixture song has one line, so the highlight stays in range.
    await page.keyboard.press('PageDown')
    await expect(page.locator('.active-line')).toHaveAttribute('data-line', '0')

    const before = await page.locator('.song-body').evaluate(
      (el) => getComputedStyle(el).fontSize,
    )
    await page.getByRole('button', { name: 'Larger text' }).click()
    const after = await page.locator('.song-body').evaluate(
      (el) => getComputedStyle(el).fontSize,
    )
    expect(parseFloat(after)).toBeGreaterThan(parseFloat(before))

    await page.keyboard.press('Escape')
    await expect(page).toHaveURL(`/songs/${song.id}`)
    await expect(page.locator('.play-stage')).toHaveCount(0)

    // Old play-mode links still work and land in performance mode.
    await page.goto(`/songs/${song.id}/play`)
    await expect(page).toHaveURL(`/songs/${song.id}?performance=1`)
    await expect(page.locator('.play-stage')).toBeVisible()
    await page.getByRole('button', { name: 'Exit performance mode' }).click()
    await expect(page).toHaveURL(`/songs/${song.id}`)
  })

  test('play view: Space on a focused toolbar button presses it', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body: '[G]One\n[C]Two\n[D]Three' } }),
    )
    await page.goto(`/songs/${song.id}/play`)
    await expect(page.locator('[data-line]')).toHaveCount(3)
    await page.getByRole('button', { name: 'Scroll' }).focus()
    await page.keyboard.press(' ')
    await expect(page.getByRole('button', { name: 'Stop' })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.active-line')).toHaveAttribute('data-line', '0')
  })

  test('play view moves the highlight across lines', async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({
        json: {
          ...song,
          body: '{start_of_verse}\n[G]One\n[C]Two\n{end_of_verse}\n\n{start_of_chorus}\n[D]Three\n{end_of_chorus}',
        },
      }),
    )
    await page.goto(`/songs/${song.id}/play`)
    await expect(page.locator('[data-line]')).toHaveCount(3)

    await page.keyboard.press('ArrowDown')
    await page.keyboard.press(' ')
    await expect(page.locator('.active-line .lyric-row')).toHaveText('Three')
    await page.keyboard.press('PageDown')
    await expect(page.locator('.active-line .lyric-row')).toHaveText('Three')

    await page.keyboard.press('PageUp')
    await expect(page.locator('.active-line .lyric-row')).toHaveText('Two')

    await page.locator('[data-line="0"]').click()
    await expect(page.locator('.active-line .lyric-row')).toHaveText('One')
    await page.getByRole('button', { name: 'Next line' }).click()
    await expect(page.locator('.active-line .lyric-row')).toHaveText('Two')

    // Modified keys are browser shortcuts, not line steps. Blur the button
    // first: Space on a focused button presses it natively.
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur())
    await page.keyboard.press('Shift+Space')
    await page.keyboard.press('Alt+ArrowDown')
    await expect(page.locator('.active-line .lyric-row')).toHaveText('Two')
  })

  test('autoscroll moves smoothly, steps speed by 0.1 and stops', async ({ page }) => {
    await page.addInitScript(() => {
      const descriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop')
      if (!descriptor?.get || !descriptor?.set) return
      let writes = 0
      Object.defineProperty(Element.prototype, 'scrollTop', {
        configurable: true,
        get() {
          return descriptor.get!.call(this)
        },
        set(value: number) {
          writes += 1
          ;(window as unknown as { __scrollWrites: number }).__scrollWrites = writes
          // Some browsers round scrollTop; the fractional accumulator must
          // still make progress.
          descriptor.set!.call(this, Math.round(value))
        },
      })
    })
    await mockApi(page)
    const lines = Array.from({ length: 80 }, (_, i) => `[G]Line ${i + 1}`).join('\n')
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body: lines } }),
    )
    await page.setViewportSize({ width: 800, height: 600 })
    await page.goto(`/songs/${song.id}`)
    const speed = page.locator('.autoscroll-controls .ctrl-label')
    const start = await page.evaluate(() => window.scrollY)

    await page.evaluate(() => {
      ;(window as unknown as { __scrollWrites: number }).__scrollWrites = 0
    })
    await page.getByRole('button', { name: 'Scroll' }).click()
    await expect(speed).toHaveText('1.0')
    await page.waitForTimeout(400)
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(start)
    // The old whole-pixel loop wrote ~4 times in 400ms; rAF now writes per frame.
    expect(
      await page.evaluate(() => (window as unknown as { __scrollWrites: number }).__scrollWrites),
    ).toBeGreaterThan(10)

    // A wheel scroll must not be immediately undone by the virtual position.
    const beforeWheel = await page.evaluate(() => window.scrollY)
    await page.mouse.wheel(0, 20)
    await page.waitForTimeout(120)
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThanOrEqual(beforeWheel + 15)

    // Hovering (no button held) must not reset the fractional position and
    // stall the scroll on browsers that round scrollTop.
    const beforeHover = await page.evaluate(() => window.scrollY)
    for (let i = 0; i < 20; i++) {
      await page.mouse.move(100 + i * 2, 120)
      await page.waitForTimeout(16)
    }
    await page.waitForTimeout(100)
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThanOrEqual(beforeHover + 2)

    await page.getByRole('button', { name: 'Faster' }).click()
    await expect(speed).toHaveText('1.1')
    await page.getByRole('button', { name: 'Slower' }).click()
    await expect(speed).toHaveText('1.0')
    await page.getByRole('button', { name: 'Faster' }).click()
    await expect(speed).toHaveText('1.1')

    // The speed survives switching to performance mode.
    await page.goto(`/songs/${song.id}/play`)
    await page.getByRole('button', { name: 'Scroll' }).click()
    await expect(page.locator('.speed')).toHaveText('1.1')
    await page.getByRole('button', { name: 'Stop' }).click()
    const stopped = await page.evaluate(() => (document.querySelector('.play-stage') as HTMLElement).scrollTop)
    await page.waitForTimeout(300)
    expect(
      await page.evaluate(() => (document.querySelector('.play-stage') as HTMLElement).scrollTop),
    ).toBe(stopped)
  })

  test('play view keeps the current line visible while autoscrolling', async ({ page }) => {
    await mockApi(page)
    const lines = Array.from({ length: 60 }, (_, i) => `[G]Line ${i + 1}`).join('\n')
    await page.route(`**/api/songs/${song.id}`, (route) =>
      route.fulfill({ json: { ...song, body: lines } }),
    )
    await page.setViewportSize({ width: 800, height: 600 })
    await page.goto(`/songs/${song.id}/play`)
    await expect(page.locator('[data-line]')).toHaveCount(60)

    await page.getByRole('button', { name: 'Scroll' }).click()
    await page.locator('body').click({ position: { x: 5, y: 590 } })
    for (let i = 0; i < 40; i++) await page.keyboard.press('ArrowDown')

    await expect(page.locator('.active-line .lyric-row')).toHaveText('Line 41')
    await expect(page.locator('.active-line')).toBeInViewport()
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

  test('prints and exports selected songs', async ({ page }) => {
    await mockApi(page)
    await page.route('**/api/songs?*', (route) =>
      route.fulfill({
        json: [song, song2],
        headers: { 'X-Total-Count': '2' },
      }),
    )
    await page.goto('/songs')
    await expect(page.locator('.song-card')).toHaveCount(2)

    await page.locator('.song-select').first().check()
    await expect(page.getByRole('button', { name: /Print selected/ })).toContainText('1')

    const exportRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith('/api/songs/export/selected') &&
        req.method() === 'POST' &&
        ((req.postDataJSON() as { ids: string[] }).ids || []).includes(song.id),
    )
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Export selected' }).click()
    await exportRequest
    expect((await download).suggestedFilename()).toContain('.cho')

    const printRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith('/api/export/selected/pdf') &&
        req.method() === 'POST' &&
        ((req.postDataJSON() as { ids: string[] }).ids || []).includes(song.id),
    )
    await page.getByRole('button', { name: /Print selected/ }).click()
    await printRequest
  })
})
