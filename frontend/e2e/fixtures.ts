import type { Page } from '@playwright/test'

export const song = {
  id: '11111111-1111-1111-1111-111111111111',
  title: 'Test Song',
  artist: 'Test Artist',
  capo: 2,
  key: 'G',
  body: [
    '{title: Test Song}',
    '{artist: Test Artist}',
    '{capo: 2}',
    '{key: G}',
    '{start_of_verse}',
    '[G]Hello [C]world',
    '{end_of_verse}',
  ].join('\n'),
  metadata: {},
  tags: ['difficulty:easy', 'genre:bluegrass'],
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const version = {
  id: '33333333-3333-3333-3333-333333333333',
  song_id: song.id,
  version: 1,
  title: 'Old Title',
  artist: 'Old Artist',
  capo: 0,
  key: null,
  body: '{title: Old Title}\n{artist: Old Artist}\n{start_of_verse}\n[G]Old line\n{end_of_verse}',
  author: 'Test User',
  created_at: '2025-12-01T00:00:00Z',
}

export const settings = {
  id: '22222222-2222-2222-2222-222222222222',
  transpose: 0,
  double_column: false,
  font: 'DejaVu Sans Mono',
  font_size: 9,
  display_mode: 'above',
}

/**
 * Mock the API so e2e tests do not need Postgres, Redis, or the FastAPI app.
 * Only paths under `/api/` are intercepted; Vite module requests continue.
 */
export async function mockApi(
  page: Page,
  {
    authenticated = true,
    unauthorized = false,
    seedAuthOnce = false,
  }: { authenticated?: boolean; unauthorized?: boolean; seedAuthOnce?: boolean } = {},
) {
  await page.addInitScript(
    ({ isAuthenticated, seedOnce }) => {
      if (!isAuthenticated) {
        localStorage.removeItem('auth')
        return
      }
      if (seedOnce && sessionStorage.getItem('e2e-auth-seeded') === '1') {
        return
      }
      localStorage.setItem('auth', JSON.stringify({ accessToken: 'e2e-token' }))
      if (seedOnce) sessionStorage.setItem('e2e-auth-seeded', '1')
    },
    { isAuthenticated: authenticated, seedOnce: seedAuthOnce },
  )

  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (!url.pathname.startsWith('/api/')) {
      return route.continue()
    }
    if (unauthorized) {
      return route.fulfill({ status: 401, json: { detail: 'Not authenticated' } })
    }
    if (url.pathname === '/api/settings') {
      return route.fulfill({ json: settings })
    }
    if (url.pathname === '/api/songs') {
      return route.fulfill({
        json: [song],
        headers: { 'X-Total-Count': '1' },
      })
    }
    if (url.pathname === `/api/songs/${song.id}`) {
      return route.fulfill({ json: song })
    }
    if (url.pathname === `/api/songs/${song.id}/analyze`) {
      return route.fulfill({ json: { suggested_key: null, confidence: null } })
    }
    if (url.pathname === `/api/songs/${song.id}/versions`) {
      return route.fulfill({ json: [version] })
    }
    if (
      url.pathname === `/api/songs/${song.id}/versions/1` &&
      route.request().method() === 'GET'
    ) {
      return route.fulfill({ json: version })
    }
    if (
      url.pathname === `/api/songs/${song.id}/versions/1/favorite` &&
      route.request().method() === 'POST'
    ) {
      return route.fulfill({
        json: { ...song, metadata: { favorite_versions: [1] } },
      })
    }
    if (
      url.pathname === `/api/songs/${song.id}/versions/1/favorite` &&
      route.request().method() === 'DELETE'
    ) {
      return route.fulfill({
        json: { ...song, metadata: { favorite_versions: [] } },
      })
    }
    if (
      url.pathname === `/api/songs/${song.id}/versions/1/fork` &&
      route.request().method() === 'POST'
    ) {
      return route.fulfill({
        json: {
          ...song,
          id: '44444444-4444-4444-4444-444444444444',
          title: 'Old Title (fork)',
          metadata: { forked_from: song.id, forked_version: 1 },
        },
      })
    }
    if (
      url.pathname === `/api/songs/${song.id}/versions/1/restore` &&
      route.request().method() === 'POST'
    ) {
      return route.fulfill({
        json: {
          ...song,
          title: version.title,
          artist: version.artist,
          capo: version.capo,
          key: version.key,
          body: version.body,
          version: 2,
        },
      })
    }
    if (url.pathname === `/api/export/song/${song.id}/pdf`) {
      return route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        body: '%PDF-1.4\n%%EOF',
      })
    }
    return route.fulfill({
      status: 404,
      json: { detail: `No e2e mock for ${url.pathname}` },
    })
  })
}
