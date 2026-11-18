# Songbook — Roadmap and Agent Guide

> **Status:** living document. Last updated: 2026-11-18.
> **Product lane:** A — personal/band songbook (see §1).
> **Owner:** @xbankov. **Audience:** maintainers and AI agents.

This document is the source of truth for **what we are building, in what order, and
why**. GitHub issues are the source of truth for **the details of each task**.
If the two disagree, fix this document in the same PR that changes the issue.

---

## 0. How to use this document

### For humans

- §1 explains the product direction.
- §4 is the ordered queue. Pick from the top.
- §7 lists what we are **not** doing (or not yet).
- §8 lists decisions that block work. Resolve these before coding.

### For AI agents

1. Read this document, `AGENTS.md`, and the issue the user asked you to work on.
   Do not pick issues yourself.
2. Check the issue against §4. If it is out of order or blocked, say so and let
   the user decide.
3. If the issue is an **epic**, do not implement it directly. Split it into
   sub-issues first (§9.4).
4. State a short plan in the session and wait for maintainer approval.
5. Branch, implement, validate, and commit (never push `main`). Stop there: the
   user pushes and opens the PR.
6. When the user asks, address the Sourcery review on the open PR (§9.3.1).
7. Update this roadmap in the same PR if the order, scope, or a decision changed
   (§10).

If anything is unclear, stop and ask.

---

## 1. Vision

> **Songbook is a private, self-hosted, print-first chordbook for a musician or a
> small band.** Import songs from the web, clean them up in ChordPro, organize
> them into songbooks/setlists, then print a reliable book/PDF or play from a
> tablet or phone — online or offline.

**Positioning:** an **open-source, self-hosted** home for your private songbook —
a **web + mobile app, similar to Immich**. Self-hosting is the focus. Running it
as a globally deployed instance is allowed and should stay possible (don't
hard-code single-host assumptions), but it is not what we optimize for (#61).

### Target user

- You, your band, and a few friends.
- People who already have songs scattered across Ultimate Guitar, Supermusic,
  pisnicky-akordy, text files, and paper.
- People who want **their own data**, no ads, and a good printed book.

### Core loop

```
Import  →  Clean up in ChordPro  →  Organize into songbooks  →  Print / Play  →  Sync offline
```

Every roadmap item should make this loop faster, more reliable, or more enjoyable.

### Principles

1. **Data ownership first.** Self-hosted, exportable, no lock-in, no ads.
2. **Single-user first.** Build and love the single-user product before adding
   accounts, roles, or ownership. Multi-user is a later data-separation layer.
3. **Print quality is a feature.** A songbook that breaks across pages is a bug.
4. **Fast curation beats endless features.** Import and edit speed matter.
5. **Offline-first mobile.** The phone must work in a rehearsal room with no signal.
6. **Small, focused PRs.** One issue per branch/PR.
7. **AI is assistive, not the product.** LLM features stay in the lab until the
   core loop is solid.

### Non-goals (for now)

- Public social network, feeds, or global discovery.
- AI-generated songs or images as a core feature.
- A marketplace, ads, or subscriptions.
- Real-time collaborative editing.
- Public registration (invite/admin-created users only).

---

## 2. Current state (verified against the code)

| Area | State |
| --- | --- |
| Song CRUD, ChordPro editor (highlight, validation, preview) | Done |
| Transposition (#2), key detection, chord diagrams | Done |
| Chord inside a word `bri[C]ght` (#15) | Done — regression test in `test_music_theory.py` |
| Title/artist/capo/key fields (#37) | Done — the fields are the source of truth. Saving strips `{title}`/`{artist}`/`{capo}`/`{key}` from the body; every export and the song view use the fields; ChordPro exports add the tags back. Existing bodies are not rewritten; old tags are ignored until the next save |
| Song view: chords above lyrics, styling, 2 columns, autoscroll (#38/#41) | Mostly done |
| Songbooks: CRUD, add/remove, PDF (#24, #89) | Done — delete/rename, reorder, per-entry transpose/columns, TOC, and metadata (author/date/genre/difficulty). The per-songbook chord chart was removed in #143; the songbook PDF uses each entry's column setting (fixed in #96) |
| Song view: chords above lyrics, styling, 2 columns, autoscroll (#38) | Done |
| Play/sing view (#41, #140) | Done — the song page has a Performance toggle: full screen, adjustable text size, current-line highlight moved by tap, arrows, Space or PageUp/PageDown (page-turner pedals), smooth shared autoscroll (#144), screen wake lock. `/songs/:id/play` redirects with `?performance=1`. Record mode stays with #42 |
| Songbooks: CRUD, add/remove, PDF (#24) | Done — delete/rename, reorder, per-entry transpose/columns, TOC; metadata → #89; the chord chart was removed in #143. The songbook PDF uses each entry's column setting (fixed in #96) |
| Import by URL + UG search/pick/import (#46, #51, #132) | Done for UG: chords merged into lyrics, sections and capo kept, one polite fetch path (#132), no page chrome or footnotes in the body (#149), and search rows show version, rating, key and difficulty (#161); supermusic blocks automated access (#133) |
| Bulk import (#29) | Done — paste, plus files/one zip with a dry run and selective import |
| Export (#54) | Done — single, selected, and all songs as ChordPro/text/ABC/LilyPond; per-songbook export is **ChordPro only** |
| Print (#55, #56, #57, #58, #59) | Done — single/selected/songbook, 1/2-column long-song layout, chords above lyrics, margins/headings/page numbers |
| Library pagination (#27) | Done |
| Version rows + list/get APIs (#45) | Done — history + restore; authors/forks/favourites/permalink split to #88 |
| Audio record/upload/playback (#42) | Partial — no record mode/privacy |
| YouTube link (#25) | Done — one link per song in song metadata (no new version); the privacy-enhanced player loads only on request |
| Tags model + API filter (#26) | Done — tag-based difficulty/genre filters, alphabet, badges |
| Auth (#68) | Done — every router except `auth` depends on `require_auth`. Public by design: `/api/health`, `/api/auth/login`, and the API docs (`/api/docs`, `/api/openapi.json`); new routes on the `auth` router are public unless they add `require_auth` themselves |
| Migrations (#69) | Done — Alembic baseline `0001`; the backend migrates on startup and adopts (stamps) an existing `init_db()` database after a schema check; CI runs upgrade/downgrade on a clean Postgres and fails on model/migration drift |

---

## 3. Pillars and epics

| Pillar | Outcome | Issues |
| --- | --- | --- |
| Foundations | Auth boundary, parser and print correctness, UI bug fixes | #68, #51, #15, #55, #33 |
| Library & songbooks | Find, filter, paginate, curate, restore versions | #26, #27, #24, #45 |
| Print & export | Print one/selected/all; clean multi-page PDF; ChordPro downloads | #54, #56, #57, #58, #44 |
| Import ecosystem | Reliable import from the sites people actually use | #29, #50, #20, #46, #28 |
| Catalog & acquisition (design) | Know which songs exist vs. which you have; a reviewable acquisition queue | #78 — epic, decisions pending (§8) |
| Performance mode | Full-screen sing/play view and recordings | #41, #42, #43, #25 |
| Mobile offline | Phone app with pre-downloaded songs and two-way sync | #70, #71 |
| Multi-user (Immich-style) | Users, roles, ownership, sharing, API keys — **after** the single-user product is liked | #72, #73, #74, #75 |
| AI lab (parked) | LLM parsing, annotations, translations, recommendations | #34, #1, #36, #40, #39, #35, #62, #49, #53, #156, #157 |
| Operations | Domain, deployment, backups | #22 |
| Pre-1.0.0 release gate | Alembic baseline (done), backup/restore, export/import, e2e | #69 |

---

## 4. Roadmap (ordered)

Sizes: **S** ≈ half day, **M** ≈ 1–3 days, **L** ≈ 1–2 weeks.

### Phase 0 — Foundations (do first)

**Status:** done (all closed by 2026-11-15).

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 1 | #68 Enforce authentication on all API routes | M | Every later feature assumes a trustworthy identity |
| 2 | #51 Fix bugs in UG parsing | M | Losing lyrics makes the core loop untrustworthy |
| 3 | #15 Chord within a word (regression test, then close) | S | Correctness; likely already fixed |
| 4 | #55 Multi-page print bug | M | Printing is the product’s main output |
| 5 | #33 Fix all the UI bugs (re-triage, close stale items) | S | Error handling and stale pre-rewrite items |

**Exit criteria:** anonymous API calls fail; known UG URLs import completely; a
long song prints without blank/clipped pages; common UI failures show a message
instead of a raw `alert()` or a silently broken page.

Migration is **not** a Phase 0 criterion; it is a pre-1.0.0 release gate.

> **Alembic (#69) is done.** Every schema change ships as a migration. The
> backend migrates on startup; an existing `init_db()` database is checked and
> stamped at the baseline, never recreated.

### Phase 1 — Library and songbooks

**Status:** done (#26, #27, #24, #45, #96, #89).

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 6 | #26 Filter by difficulty/genre/artist/alphabet | M | A growing songbook needs retrieval |
| 7 | #27 Pagination | M | The UI currently shows at most 50 songs |
| 8 | #24 Songbook completion (TOC, sorting, per-entry settings, delete/rename) | L | The songbook is the core artifact |
| 9a | ~~#96 Songbook PDF ignores a per-entry single-column setting~~ (done) | S | Bug; PDF disagrees with the screen view |
| 9b | ~~#89 Songbook metadata + chord-scheme selection~~ (done) | M | Columns on `songbooks` via migration `0002` |
| 9 | #45 Version history UI + restore (authors/forks/favourites → #88) | M | Editing must be safe |

**Resolved:** #26 stores difficulty and genre as tags (`difficulty:*`,
`genre:*`); #27 can build pagination on the same filters.

### Phase 2 — Print and export

**Status:** #54, #56, #57, #58 done (plus #55, #59, #143); only #44 remains
(needs a spec for "starting note" and "rhythmic pattern"; `capo`/`key` already
exist).

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 10 | #54 Download ChordPro for one/selected/all | S | Data ownership; also feeds #28 |
| 11 | #56 Print buttons (single/selected/book) | M | The main workflow |
| 12 | #57 Chord signs in print/PDF | S | Chords should look like chords |
| 13 | #58 Print looks (margins, headings, page numbers) | S | Polish |
| 14 | #44 Expand ChordPro tags | S | Starting note/rhythm are the only gaps |
| 14a | ~~#143 Remove the end-of-songbook chord chart~~ (done) | S | Redundant once chords are clickable; shorter printed books |

### Phase 3 — Import ecosystem

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 15 | ~~#29 Batch upload: files and one zip, dry run then import~~ (done) | M | Bring an existing library in at once; base for #134 |
| 15a | ~~#132 UG import: merge chords into lyrics, keep sections and capo~~ (done) | M | UG is the main import source |
| 15b | ~~#149 UG import: strip the tab header, textual capo and footnote/tab blocks~~ (done) | S | Imports still carried page chrome |
| 15c | ~~#161 Import search: version, rating, key, difficulty and source link~~ (done) | S | Ten identical rows cannot be told apart |
| 16 | #50 Import pisnicky-akordy.cz | M | The other site this circle uses |
| 17 | #20 Harden Supermusic import (~~#133 anti-bot stub → clear error~~ done) | M | Song pages sit behind a JS proof-of-work challenge we will not solve; paste is the fallback |
| 18 | #46 Direct lookup by name (narrow to extra sources) | S | UG flow already exists |
| 19 | #28 Import/export a Git repo | L | Data ownership and versioned backups |

**In progress — #151 Import v2 epic (lists, playlists, bookmarks, refresh).**
A container for the import rework: reference → match → acquisition → review →
import → provenance. Sub-issues so far: #152 (pipeline/provenance), #153
(reference lists), #154 (Spotify playlists), #155 (refresh from source). It is a
discuss epic: resolve its decisions and schedule the sub-issues before coding.
Related tracks that stay in their own phases: #156 (AI chord acquisition, Phase
7), #157 (AI cleanup, Phase 7), #158 (AI setlists, Phase 7), #159 (practice
toolbox).

**Not scheduled — #78 catalog & acquisition epic ("Lidarr for chord sheets").**
A MusicBrainz-backed metadata catalog plus a reviewable acquisition queue. It is a
design epic: resolve its open decisions (§8) and split it (§9.4) before any code.
The issue itself recommends starting only after the Alembic baseline (#69).

### Phase 4 — Performance mode

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 20 | ~~#41 Play/sing view (full-screen, current-line highlight)~~ (done) | M | Rehearsal/gig use |
| 21 | #42 + #43 Recordings/attachments (merge) | L | Useful, but larger |
| 21a | ~~#140 Merge play mode into the song view (Performance toggle)~~ (done) | M | One reading surface; `/songs/:id/play` redirects |
| 21b | ~~#144 Smooth autoscroll with finer speed~~ (done) | S | One shared animation loop; no 10 Hz jumps |
| 21c | #141 Suggested key: explain and apply it | S | The suggestion is opaque |
| 21d | #142 Clickable chords with a chord-scheme dropdown | M | Diagrams where the player looks |
| 22 | ~~#25 YouTube link~~ (done) | S | Small reference feature |

**Performance follow-ups:** #141, then #142; both build on the merged #140/#144
song view. #143 removed the end-of-book chart that #142 replaces.

### Phase 5 — Mobile offline (single-user)

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 23 | #71 Design v1 sync protocol and change tracking | M | Correctness before UI |
| 24 | #70 Mobile app epic | L | Umbrella; split into sub-issues |

**Recommended stack:** reuse the Vue 3 app with **Capacitor** + **PWA**, local
**SQLite**, and a delta sync protocol. The repo already has Capacitor packages
and a PWA plugin.

**Single-user assumption:** v1 sync must use a scoped, revocable per-device API
key. Implement a minimal single-user key list (create/list/revoke, hashed at
rest) with the mobile work; #75 later scopes keys per user. Do not add `owner_id`
or roles just for mobile, and do not use a shared or non-revocable token.

**Exit criteria:** airplane-mode read of downloaded songs; offline edits sync
once; deletions propagate; a revoked device stops syncing; storage use is visible.

### Phase 6 — Multi-user and data separation (later)

Do **not** start this until the single-user product is liked. It is a
data-separation layer, not a prerequisite for the core loop.

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 25 | #72 Multi-user epic | L | Umbrella; split into sub-issues |
| 26 | #73 Users, roles, and ownership schema | L | Data separation |
| 27 | #74 Admin user management | M | Create/disable users, reset passwords |
| 28 | #75 API keys for mobile/CLI sync | M | Per-user device access |
| 29 | Sharing (songbook view/edit, partner/whole-library) | L | Create after #72 is split |
| 30 | Sessions/refresh/revoke + trash/restore | M | Account safety and recovery |
| 31 | #88 Version authors, forking, favourites, permalinks | M | Depends on users/ownership |

**Recommendation:** invite-only users; admin-created accounts; no public
registration. Do not build quotas or billing.

**Before this phase:** if schema changes must preserve data, add the Alembic
baseline (#69) first.

### Phase 7 — AI lab (only after the core loop is solid)

#34 (chord validation + hover diagrams) → #1 (chord schemes/blacklist) →
#36 annotations → #40 translations → #39 AI graphics → #35 creative mode →
#62 recommendations → #49 auto-transcribe → #53 LLM parsing → #156 AI chord
acquisition → #157 AI cleanup of imported ChordPro → #158 AI setlist generation.

Treat these as experiments: time-boxed, behind a flag if possible, and never on
the critical path. #149 (deterministic import cleanup) is done; #157 is the LLM
assist for what the rules cannot catch.

### Phase 8 — Operations

~~#22 Custom domain + TLS~~ (done): `docker-compose.tls.yml` adds Caddy with automatic Let's Encrypt HTTPS; guide in [`docs/deployment.md`](deployment.md).

~~Auto-deploy tagged releases~~ (done): the private `home-server` repository
holds the app as a submodule and a self-hosted GitHub Actions runner deploys
the newest `v*` tag every ten minutes, with a pre-deploy `pg_dump` and a
health-check rollback; guide in [`docs/deployment.md`](deployment.md#5-releases-and-auto-deploy-home-server).

### Pre-1.0.0 release gate

Do these before tagging 1.0.0:

- ~~#69 Add the Alembic baseline~~ (done; both upgrade paths are tested in CI):
  - fresh database: `alembic upgrade head`
  - existing `init_db()` database: checked, stamped at `0001`, then upgraded
- Never recreate or reset a database that contains real data.
- Back up and restore a real database.
- Export and re-import the whole library.
- e2e + CI green; no known data-loss bugs.
- Document the upgrade path in the README.

---

## 5. Mobile offline plan

### Architecture

- **Client:** Capacitor wrapper around the existing Vue app + PWA fallback.
- **Local data:** SQLite (songs, songbooks, tags, settings, sync metadata).
- **Auth:** v1 (single-user) uses a scoped, revocable per-device API key, stored
  hashed. The key list is single-user now; #75 scopes keys per user later.
- **Sync:** server-authoritative, delta-based, idempotent.
- **Offline packs:** explicit download of a songbook or the whole library;
  attachments/audio are optional and size-aware.

> Mobile v1 assumes **one user**. Do not add `owner_id`, roles, or ownership
> scoping just for sync; that belongs to Phase 6.

### Sync model (v1 proposal)

- Every syncable row has `updated_at`; deletes are soft deletes/tombstones.
- Server exposes a cursor-based change feed.
- The client stores a cursor plus an **outbox** of local mutations.
- Push includes the client’s base version; the server returns a conflict if stale.
- Conflict policy v1: last-write-wins per record, with a visible warning; no silent
  data loss. Section-level merge can come later.
- Retries are idempotent via client-generated ids.

### What “pre-downloaded everything” means

- All songs and songbooks the user has access to.
- Metadata: title, artist, capo, key, tags, songbook order.
- Attachments/audio/images: opt-in per songbook, Wi-Fi-only by default.
- A “storage” screen showing usage and a “remove download” action.

### Risks

- Sync bugs can lose user edits — test hard.
- Audio/attachments can be large — make them opt-in.
- iOS distribution has more friction than Android; Android first.

---

## 6. Multi-user plan (Immich-style)

> **Later layer.** Do not start until the single-user product is liked. The goal
> is data separation and sharing, not a prerequisite for the core loop.

### Mapping

| Immich | Songbook |
| --- | --- |
| User + admin/user role | Same |
| Personal library | Personal songs, songbooks, tags, settings |
| Album | Songbook |
| Shared album / partner sharing | Share a songbook (view/edit) or a whole library |
| API key | Per-device/CLI sync key |
| Admin server settings | Instance settings, user management |
| Favourites | Favourites (enables recommendations later) |
| Trash/restore | Soft-delete + restore |
| OAuth/OIDC | Optional login provider |

### Migration

1. Add the Alembic baseline (#69) before changing the schema.
2. Add `users` with roles.
3. Add nullable `owner_id` to songs/songbooks/tags/settings.
4. Create a bootstrap admin.
5. Backfill existing rows to the admin.
6. Make `owner_id` non-null and add indexes.
7. Enforce ownership on every route and test cross-user access.

### Security invariants

- No route returns another user’s data.
- Sharing grants exactly `view` or `edit`, and is revocable.
- Admin actions cannot remove the last active admin.
- API keys are hashed, scoped, revocable, and show `last_used_at`.
- Disabling a user or resetting a password revokes sessions.

### Non-goals (v1)

Public registration, global search across users, real-time collaboration,
quotas/billing, public profiles.

---

## 7. Deprecated, parked, and needs clarity

### Close/verify as done

Closed 2026-11-16: #2 Transposition (implemented), #38 Improve song view
(implemented), #61 SongBook vs UG (answered by §1).

Not yet: #60 (where lyrics come from) stays open until the import policy (§8.7)
is written down.

Still open; needs a small follow-up first:

- #46 Direct lookup by name — UG flow exists; narrow the issue to extra sources.

Closed: #15 (regression test added), #33 (re-triaged), #37 (fields replace body tags).

### Park / close as out of scope (for Lane A)

- #47 Browser bookmarks import — web apps can’t read bookmarks; needs an extension
  or a bookmark-file upload. Park.
- #48 UG playlist import — ToS/technical fragility. Park.
- #52 Browser extension — out of scope for a self-hosted web app. Park.
- #49 Auto-transcribe — research project. Park.
- #39 AI-generated graphics — cosmetic. Park.
- #35 Creative mode — too vague. Park.
- #42 Social/video record mode — keep only the “attach a recording” part (#43).
- ~~#22 Domain name~~ — done as an ops guide + Caddy override.
- #60 Where do lyrics come from? — policy decision; document and close.

### Needs a written spec before coding

- #43 Attachments — which file types, storage, privacy?
- #44 Expand ChordPro — semantics of “starting note” and “rhythmic pattern”.
- #23 User management — superseded by the multi-user epic (#72).
- #34 WYSIWYG — split editor improvements from AI suggestions.
- #36 Annotations — data model and permissions.
- #40 Translations — languages, source, licensing.
- #53 LLM parsing — acceptance criteria and cost.
- #62 Recommendations — which signals (favourites, history, tags).
- #60 — a decision, not a feature.

---

## 8. Open decisions

> Items marked **later** belong to the multi-user layer; do not block the
> single-user roadmap on them.

1. **#55 print layout (resolved).** Print layout is configurable: a dedicated
   print view with a 1/2-column toggle (defaulting to the saved column setting),
   app chrome hidden, chord+lyric pairs kept together, short sections (≤10
   lines) kept whole, and long sections allowed to flow across pages (#84).
2. **Registration model (later).** Invite-only vs open. Recommendation:
   invite-only.
3. **Login identifier (later).** Email vs username. Recommendation: email +
   optional display name.
4. **Sync conflicts.** Last-write-wins vs manual resolution. Recommendation: LWW
   per record for v1, with a warning.
5. **Attachments.** Which types and where stored (DB vs object storage).
6. **Metadata model (resolved).** Difficulty and genre are tags (`difficulty:*`,
   `genre:*`); see #26. Other metadata stays flexible.
7. **Import policy.** Keep source URLs, private use, deletion on request; document
   it in the README.
8. **Mobile stack.** Capacitor + Vue vs a separate native app. Recommendation:
   Capacitor + Vue + PWA.
9. **#89 songbook metadata storage (resolved).** Dedicated nullable columns
   (`author`, `date`, `genre`, `difficulty`) added by migration `0002`. The
   `chord_diagrams` column from the same migration is kept for existing data
   but is no longer read or exposed: the chart was removed in #143.
10. **#78 catalog & acquisition (blocking #78).** Approve the catalog / library /
    acquisition model; MusicBrainz work/recording MBIDs as canonical identity;
    the source policy (UG manual-only, no public chord catalog); whether to retire
    `backend/crawler.py` bulk import; and the first slice to build.
11. **Play mode (#140) (resolved).** Fold the separate play view into the song
    page as a Performance toggle, and redirect `/songs/:id/play` to
    `/songs/:id?performance=1` so old links and bookmarks keep working.
12. **AI cleanup (#157).** Provider (OpenAI-compatible vs a specific vendor),
    key storage (env vs DB), on-demand vs automatic, preview, privacy/cost, and
    whether to pull it into Phase 3 after #149. Recommendation: on-demand,
    preview always, Phase 7 unless #149 leaves too much garbage.

---

## 9. Agent operating manual

### 9.1 Read order

1. `AGENTS.md` — repository rules and validation.
2. This roadmap — direction and order.
3. The issue + its comments — scope and acceptance criteria.
4. The relevant code and tests.

### 9.2 Pick work

- Work on **one issue at a time**: the one the user asked for.
- The user normally asks from the top of §4. If the requested issue is out of
  order, point that out; proceed only if the maintainer confirms.
- Do not start an **epic** directly; split it first.
- If the issue is blocked, ask; do not guess.

### 9.3 Plan and approval

- Post a short plan: what changes, what does not, how it will be tested, risks.
- Wait for maintainer approval before coding.
- If the plan changes after approval, say so before proceeding.

### 9.3.1 Review gate (Sourcery)

A PR is never “ready” after the first CI run. It must pass this gate:

- CI is green on the **latest** commit.
- Sourcery has reviewed the **latest** commit.
- Every Sourcery finding is fixed, or explicitly answered with a reason.
- Push the fixes and wait for a fresh review; repeat until no blocking findings.

If a Sourcery finding is unclear, ask the maintainer. Do not ignore, dismiss, or
silently skip it.

Dependabot minor/patch PRs are the exception: they auto-merge once the required checks
"CI passed" and "Sourcery review" succeed (see the decision log).

### 9.4 Epics

An epic is too large for one PR. Before starting it:

- Split it into issues that each fit one PR.
- Each sub-issue gets its own acceptance criteria and dependencies.
- Link sub-issues with “Part of #<epic>”.
- Add the sub-issues to §4 and update the roadmap.

### 9.5 Implementation rules

- Branch from an up-to-date `main`: `fix/<issue>-<topic>` or `feat/<issue>-<topic>`.
- Python: type hints, black, isort.
- Frontend: `npm run build` must pass; do not commit `dist/`.
- UI: `npm run test:e2e` must pass; add a Playwright test for user-facing behavior.
- **Single-user first:** until Phase 6, do not add `users`, `owner_id`, roles, or
  ownership checks. Multi-user is a later data-separation layer.
- **Schema changes:** ship an Alembic migration (`alembic revision
  --autogenerate`, reviewed) that preserves data and downgrades. Never reset a
  real database.
- Tests: add or update tests for behavior changes; never weaken tests to pass.
- Keep PRs small and focused on one issue.
- You may edit `.github/` and `docker-compose.yml` when the task requires it;
  explain why in the PR. Never commit `.env` or secrets.
- Do not upgrade dependencies or reformat unrelated files.
- Never push to `main`; never merge.

### 9.6 Definition of done

- Acceptance criteria met.
- Tests added/updated.
- Validation passes:
  ```sh
  isort --check-only backend/app
  black --check backend/app
  cd backend && pytest -q app/tests
  cd frontend && npm run build
  cd frontend && npm run test:e2e
  ```
- Roadmap updated if order/scope/decision changed.
- Sourcery reviewed the latest commit; every finding fixed or explicitly answered.
- PR description follows the format: `Closes #<issue>`, what changed, validation,
  risk, rollback, and Sourcery status.

### 9.7 When to stop and ask

- The issue is ambiguous or has no acceptance criteria.
- A change would affect data safety, auth, or another user’s data.
- The work is larger than one PR.
- You need a product decision (§8).
- Tests fail for reasons unrelated to your change.

Ask in the session or on the issue.

### 9.8 Roadmap maintenance

Update this file in the **same PR** when:

- an issue is added, split, closed, or reprioritized;
- a phase starts or finishes;
- a decision in §8 is made (add it to the decision log);
- the product direction changes.

Keep the changelog at the bottom current. Do not rewrite history; append.

---

## 10. Decision log

| Date | Decision | By |
| --- | --- | --- |
| 2026-11-15 | Product lane A: personal/band songbook, print-first, self-hosted | @xbankov |
| 2026-11-15 | Mobile: offline-capable app that syncs with the server | @xbankov |
| 2026-11-15 | Multi-user eventually, modeled on Immich | @xbankov |
| 2026-11-15 | Work issue-by-issue; discuss before implementing | @xbankov |
| 2026-11-15 | Playwright e2e is the UI validation; remove the `.ai/validate.sh` wrapper | @xbankov |
| 2026-11-15 | Remove Codacy from the PR pipeline; run it on main/nightly if wanted | @xbankov |
| 2026-11-15 | `.github/` and `docker-compose.yml` may be edited when needed; never commit secrets | @xbankov |
| 2026-11-15 | Every PR waits for the Sourcery review on the latest commit and addresses all findings before it is ready or merged | @xbankov |
| 2026-11-15 | Single-user functionality first; multi-user/data separation is a later layer (Phase 6), started only when the single-user product is liked | @xbankov |
| 2026-11-15 | Alembic is deferred for dev/empty databases; it is required before changing a schema under real data and at the pre-1.0.0 release gate. Never reset a real database | @xbankov |
| 2026-11-15 | Difficulty and genre use tags (`difficulty:*`, `genre:*`); no new columns (#26) | @xbankov |
| 2026-11-15 | Version history/restore ships now; version authors, forking, favourites, and permalinks are deferred to #88 with multi-user | @xbankov |
| 2026-11-15 | Songbook core (delete/rename, reorder, per-entry settings, TOC) ships now; metadata/chordscheme split to #89 pending a schema decision | @xbankov |
| 2026-11-15 | Long-song print layout is configurable (1/2 columns), not forced to one column (#55) | @xbankov (via #84) |
| 2026-11-16 | Positioning: open-source, self-hosted private songbook (web + mobile, Immich-like); a global deployment is allowed but not the focus (#61) | @xbankov |
| 2026-11-16 | Title, artist, capo and key live in song fields; body tags are stripped on save and added only on ChordPro export; stored bodies are not rewritten (#37) | @xbankov |
| 2026-11-16 | The running instance holds a real library: #69 (Alembic baseline) precedes any schema change, starting with #89 | @xbankov |
| 2026-11-16 | Dependabot minor/patch PRs auto-merge (rebase) once the required checks "CI passed" and "Sourcery review" succeed; majors need a manual review. This is the only exception to the human review gate (§9.3.1) | @xbankov |
| 2026-11-16 | #89: songbook metadata in dedicated columns; chord chart per songbook (none/uncommon/all) on the page and in the PDF, using the same open-position shape rule on both | agent (user asked to continue the roadmap) |
| 2026-11-17 | #29: file/zip batch upload is two calls over the same files — a dry run that lists songs, duplicates and errors, then an import of the selected entries. ChordPro keeps non-metadata directives; plain text uses the UG parser; archives are read in memory with limits and never extracted to disk. Titles fall back to the file name | agent (user approved the spec in session) |
| 2026-11-17 | #144: the song view and performance mode share one `requestAnimationFrame` autoscroll with fractional pixels, 0.1 speed steps (0.1–10, default 1), a persisted speed, and a stop at the end | agent (user asked to continue the roadmap) |
| 2026-11-17 | #140: performance mode is a toggle on the song page; `/songs/:id/play` redirects to `?performance=1` rather than 404ing old links | @xbankov (asked in session) |
| 2026-11-17 | #143: remove the end-of-songbook chord chart from the page, PDF and API; keep the `chord_diagrams` column for existing data. Reverses the chart part of the #89 decision | agent (user asked to continue the roadmap) |
| 2026-11-17 | #149: a UG tab drops its leading title/artist/URL/textual-capo header, tab staff lines, chord `*`/`xN` markers, and the trailing notes/alternate-chord block. The capo comes from the metadata; no network in tests | agent (user asked to continue the roadmap) |
| 2026-11-17 | #161: UG search keeps version/total versions, rating/votes, key, difficulty, update date, verified and type label; rows deduplicate identical URLs and default to a vote-weighted best order, with local best/votes/newest sorting | agent (user asked to continue the roadmap) |
| 2026-11-18 | #151 is the container epic for import v2 (sub-issues #152–#155); #156/#157 are Phase 7 AI follow-ups, with #157 on-demand and preview-first | agent (user asked to continue the roadmap) |
| 2026-11-17 | Releases are `v*` tags on `main`; production runs on the home server from the private `home-server` repo (submodule + own Compose project) and a self-hosted runner deploys the newest tag with a pre-deploy `pg_dump` and a health-check rollback | agent (user chose in session) |

---

## 11. Changelog

| Date | Change |
| --- | --- |
| 2026-11-15 | Initial roadmap: Lane A, phase order, mobile and multi-user epics, agent rules |
| 2026-11-15 | Removed `.ai/validate.sh`; added Playwright e2e as UI validation |
| 2026-11-15 | CI: removed Codacy, added path filters/caching/parallel jobs, Docker push on main only |
| 2026-11-15 | Added the Sourcery review gate: wait for the latest review and address every finding |
| 2026-11-15 | Reordered the roadmap: single-user library/print/import before mobile; multi-user moved to Phase 6; Alembic deferred to pre-1.0.0 |
| 2026-11-15 | Clarified Alembic data-safety/stamp paths, required revocable per-device keys for sync, and made queue ranks unique |
| 2026-11-15 | #26 implemented with tag-based difficulty/genre filters, alphabet index, and card badges |
| 2026-11-15 | #45 history/restore implemented; authors/forks/favourites/permalink split to #88 |
| 2026-11-15 | #24 songbook core implemented; metadata/chordscheme split to #89 |
| 2026-11-16 | Housekeeping: refreshed §2 against the code; marked Phases 0–2 status; added #78 (unscheduled) and the #89/#78 decisions; resolved the #55 decision; listed issues to close |
| 2026-11-16 | Retired the `ai:` label workflow and `.ai-loop.toml`; agents work only on user-requested issues, the user pushes and opens PRs, and agents address Sourcery review on request |
| 2026-11-16 | Added the #61 positioning to §1; closed #2, #38, #61 |
| 2026-11-16 | #96 fixed: songbook PDF respects each entry's column setting |
| 2026-11-16 | #37 done: song fields replace body metadata tags; #69 ordered before #89 |
| 2026-11-16 | CI: added the "CI passed" gate job and Dependabot auto-merge |
| 2026-11-16 | Dependabot: grouped coupled packages (pytest, celery/redis, TypeScript/vue-tsc, Capacitor, pinia, vite, eslint) across all update types; TypeScript 7 ignored until vue-tsc supports it |
| 2026-11-16 | #69 done: Alembic baseline `0001`, startup migration with `init_db()` adoption, CI migration checks |
| 2026-11-16 | #25 done: per-song YouTube link; song API now returns `metadata` (was `metadata_`, which the UI never read) |
| 2026-11-16 | #22 done: custom domain + automatic HTTPS via a Caddy Compose override; `docs/deployment.md` |
| 2026-11-16 | #89 done: songbook metadata and chord-diagram selection (migration `0002`) |
| 2026-11-16 | #41 done: play/sing view with current-line highlight and pedal keys |
| 2026-11-17 | #133 fixed: supermusic's anti-bot stub gives a clear import error instead of an empty song |
| 2026-11-17 | #132 fixed: UG import merges chord lines into lyrics, maps sections, saves capo/key, lists only importable search results, and uses one rate-limited fetch path |
| 2026-11-17 | #29 done: batch upload of files or one zip, with a dry run, duplicate flags, selective import, and zip-safety limits |
| 2026-11-17 | #144 done: smooth shared autoscroll in the song and play views, 0.1 speed steps, shared/persisted speed, and a stop at the end |
| 2026-11-17 | #140 done: play mode folded into the song page as a Performance toggle; `/songs/:id/play` redirects; one SongDisplay and one autoscroll implementation |
| 2026-11-17 | #143 done: removed the songbook chord chart from the page, PDF and API; the column stays for existing data |
| 2026-11-17 | #149 done: UG imports drop the tab header, textual capo, staff lines, trailing notes/alternate-chord blocks, and chord markers |
| 2026-11-17 | #161 done: UG search rows show type, version, rating/votes, key, difficulty, update year and verified state, with a source link and best/votes/newest sort |
| 2026-11-18 | Added the #151 Import v2 epic notes and the #156/#157 AI follow-ups; #141/#142 scheduled next in Phase 4 |
| 2026-11-17 | Auto-deploy: tagged releases are rolled out to the home server by a self-hosted runner (submodule + own Compose project); guide in docs/deployment.md §5 |
