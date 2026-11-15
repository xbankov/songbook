# Songbook — Roadmap and Agent Guide

> **Status:** living document. Last updated: 2026-11-15.
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

1. Read this document, `AGENTS.md`, and the issue you are about to work on.
2. Pick **one** issue from §4, in order, that is not blocked.
3. If the issue is an **epic**, do not implement it directly. Split it into
   sub-issues first (§9.4).
4. State a short plan in the session and wait for maintainer approval.
5. Branch, implement, validate, commit, and open a PR (never push `main`).
6. Update this roadmap in the same PR if the order, scope, or a decision changed
   (§10).

If anything is unclear, stop and ask. Use the `ai:waiting-for-input` label.

---

## 1. Vision

> **Songbook is a private, self-hosted, print-first chordbook for a musician or a
> small band.** Import songs from the web, clean them up in ChordPro, organize
> them into songbooks/setlists, then print a reliable book/PDF or play from a
> tablet or phone — online or offline.

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
2. **Print quality is a feature.** A songbook that breaks across pages is a bug.
3. **Fast curation beats endless features.** Import and edit speed matter.
4. **Offline-first mobile.** The phone must work in a rehearsal room with no signal.
5. **Small, focused PRs.** One issue per branch/PR.
6. **AI is assistive, not the product.** LLM features stay in the lab until the
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
| Chord inside a word `bri[C]ght` (#15) | Parser/renderer supports it; add a regression test |
| Separate title/artist fields (#37) | Done in the edit UI; normalize body tags on save |
| Song view: chords above lyrics, styling, 2 columns, autoscroll (#38/#41) | Mostly done |
| Songbooks: CRUD, add/remove, PDF (#24) | Partial — no TOC, metadata, sorting UI, per-entry settings, delete UI |
| Import by URL + UG search/pick/import (#46) | Mostly done for UG |
| Bulk paste import; bulk ChordPro/text/ABC/LilyPond export (#29/#54) | Partial — no file upload, no single/selected export UI |
| Print single song + songbook PDF (#56) | Partial — no multi-select |
| Version rows + list/get APIs (#45) | Partial — no history/restore UI |
| Audio record/upload/playback (#42) | Partial — no record mode/privacy |
| Tags model + API filter (#26) | Partial — no tag/difficulty/genre UI |
| Auth | ⚠️ Login exists, but **no API route uses `require_auth`** |
| Migrations | ⚠️ `init_db()` creates tables; `backend/migrations/versions/` is empty |

---

## 3. Pillars and epics

| Pillar | Outcome | Issues |
| --- | --- | --- |
| Foundations | Trustworthy auth, migrations, parser and print correctness | #68, #69, #51, #15, #55 |
| Library & songbooks | Find, filter, paginate, curate, restore versions | #26, #27, #24, #45 |
| Print & export | Print one/selected/all; clean multi-page PDF; ChordPro downloads | #54, #56, #57, #58, #44 |
| Import ecosystem | Reliable import from the sites people actually use | #29, #50, #20, #46, #28 |
| Mobile offline | Phone app with pre-downloaded songs and two-way sync | #70, #71, #75 |
| Multi-user (Immich-style) | Users, roles, ownership, sharing, API keys | #72, #73, #74 |
| Performance mode | Full-screen sing/play view and recordings | #41, #42, #43, #25 |
| AI lab (parked) | LLM parsing, annotations, translations, recommendations | #34, #1, #36, #40, #39, #35, #62, #49, #53 |
| Operations | Domain, deployment, backups | #22 |

---

## 4. Roadmap (ordered)

Sizes: **S** ≈ half day, **M** ≈ 1–3 days, **L** ≈ 1–2 weeks.

### Phase 0 — Foundations (do first)

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 1 | #68 Enforce authentication on all API routes | M | Every later feature assumes a trustworthy identity |
| 2 | #69 Add Alembic migrations for the current schema | M | Users and sync need safe schema upgrades |
| 3 | #51 Fix bugs in UG parsing | M | Losing lyrics makes the core loop untrustworthy |
| 4 | #15 Chord within a word (regression test, then close) | S | Correctness; likely already fixed |
| 5 | #55 Multi-page print bug | M | Printing is the product’s main output |
| 6 | #33 Fix all the UI bugs (re-triage, close stale items) | S | The listed bugs are from the pre-rewrite app |

**Exit criteria:** anonymous API calls fail; a clean DB can be migrated; known UG
URLs import completely; a long song prints without blank/clipped pages.

### Phase 1 — Library and songbooks

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 7 | #26 Filter by difficulty/genre/artist/alphabet | M | A growing songbook needs retrieval |
| 8 | #27 Pagination | M | The UI currently shows at most 50 songs |
| 9 | #24 Songbook completion (TOC, metadata, sorting, per-entry settings) | L | The songbook is the core artifact |
| 10 | #45 Version history UI + restore | M | Editing must be safe |

**Dependency note:** #26 and #27 need a decision on whether difficulty/genre are
real columns, tags, or JSON metadata. Decide before coding.

### Phase 2 — Print and export

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 11 | #54 Download ChordPro for one/selected/all | S | Data ownership; also feeds #28 |
| 12 | #56 Print buttons (single/selected/book) | M | The main workflow |
| 13 | #57 Chord signs in print/PDF | S | Chords should look like chords |
| 14 | #58 Print looks (margins, headings, page numbers) | S | Polish |
| 15 | #44 Expand ChordPro tags | S | Starting note/rhythm are the only gaps |

### Phase 3 — Mobile offline (Lane A differentiator)

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 16 | #73 Users, roles, and ownership schema | L | Needed for per-user libraries and API keys |
| 17 | #75 API keys for mobile/CLI sync | M | Never ship the admin password in an app |
| 18 | #71 Design v1 sync protocol and change tracking | M | Correctness before UI |
| 19 | #70 Mobile app epic | L | Umbrella; split into sub-issues |

**Recommended stack:** reuse the Vue 3 app with **Capacitor** + **PWA**, local
**SQLite**, and a delta sync protocol. The repo already has Capacitor packages
and a PWA plugin.

**Exit criteria:** airplane-mode read of downloaded songs; offline edits sync
once; deletions propagate; a revoked device stops syncing; storage use is visible.

### Phase 4 — Multi-user (Immich-style)

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 20 | #72 Multi-user epic | L | Umbrella; split into sub-issues |
| 21 | #74 Admin user management | M | Create/disable users, reset passwords |
| 22 | Sharing (songbook view/edit, partner/whole-library) | L | Create after #72 is split |
| 23 | Sessions/refresh/revoke + trash/restore | M | Account safety and recovery |

**Recommendation:** invite-only users; admin-created accounts; no public
registration in v1. Do not build quotas or billing.

### Phase 5 — Performance mode

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 24 | #41 Play/sing view (full-screen, current-line highlight) | M | Rehearsal/gig use |
| 25 | #42 + #43 Recordings/attachments (merge) | L | Useful, but larger |
| 26 | #25 YouTube link | S | Small reference feature |

### Phase 6 — AI lab (only after the core loop is solid)

#34 (chord validation + hover diagrams) → #1 (chord schemes/blacklist) →
#36 annotations → #40 translations → #39 AI graphics → #35 creative mode →
#62 recommendations → #49 auto-transcribe → #53 LLM parsing.

Treat these as experiments: time-boxed, behind a flag if possible, and never on
the critical path.

### Phase 7 — Operations

#22 Custom domain + TLS. This is an ops checklist, not application code.

---

## 5. Mobile offline plan

### Architecture

- **Client:** Capacitor wrapper around the existing Vue app + PWA fallback.
- **Local data:** SQLite (songs, songbooks, tags, settings, sync metadata).
- **Auth:** per-device API key, revocable, scoped.
- **Sync:** server-authoritative, delta-based, idempotent.
- **Offline packs:** explicit download of a songbook or the whole library;
  attachments/audio are optional and size-aware.

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

1. Add `users` with roles.
2. Add nullable `owner_id` to songs/songbooks/tags/settings.
3. Create a bootstrap admin.
4. Backfill existing rows to the admin.
5. Make `owner_id` non-null and add indexes.
6. Enforce ownership on every route and test cross-user access.

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

- #2 Transposition — implemented.
- #15 Chord within a word — add a regression test, then close.
- #37 Title/artist outside lyrics — finish tag normalization, then close.
- #38 Improve song view — remaining work is print parity (#57).
- #46 Direct lookup by name — UG flow exists; narrow to extra sources.
- #33 Fix all UI bugs — stale, pre-rewrite.

### Park / close as out of scope (for Lane A)

- #47 Browser bookmarks import — web apps can’t read bookmarks; needs an extension
  or a bookmark-file upload. Park.
- #48 UG playlist import — ToS/technical fragility. Park.
- #52 Browser extension — out of scope for a self-hosted web app. Park.
- #49 Auto-transcribe — research project. Park.
- #39 AI-generated graphics — cosmetic. Park.
- #35 Creative mode — too vague. Park.
- #42 Social/video record mode — keep only the “attach a recording” part (#43).
- #22 Domain name — ops checklist, not code.
- #60 Where do lyrics come from? — policy decision; document and close.
- #61 SongBook vs UG — answered by §1 (Lane A); record the decision and close.

### Needs a written spec before coding

- #29 Batch upload — paste (already done) or file/zip upload?
- #43 Attachments — which file types, storage, privacy?
- #44 Expand ChordPro — semantics of “starting note” and “rhythmic pattern”.
- #23 User management — superseded by the multi-user epic (#72).
- #34 WYSIWYG — split editor improvements from AI suggestions.
- #36 Annotations — data model and permissions.
- #40 Translations — languages, source, licensing.
- #53 LLM parsing — acceptance criteria and cost.
- #62 Recommendations — which signals (favourites, history, tags).
- #60/#61 — decisions, not features.

---

## 8. Open decisions

1. **#55 print layout (blocking).** The bot session on #55 asked for input but the
   question was not written into the issue. The decision needed is:
   - Do we print long songs in **one column** (reliable) or keep **two columns**
     and implement proper pagination?
   - Do chord diagrams, audio controls, and the version footer belong in print?
   - **Recommendation:** one column for print, hide chord diagrams/audio/footer,
     keep chord+lyric pairs together, and paginate at section boundaries.
2. **Registration model.** Invite-only vs open. Recommendation: invite-only.
3. **Login identifier.** Email vs username. Recommendation: email + optional
   display name.
4. **Sync conflicts.** Last-write-wins vs manual resolution. Recommendation: LWW
   per record for v1, with a warning.
5. **Attachments.** Which types and where stored (DB vs object storage).
6. **Metadata model.** Difficulty/genre as columns, tags, or JSON.
7. **Import policy.** Keep source URLs, private use, deletion on request; document
   it in the README.
8. **Mobile stack.** Capacitor + Vue vs a separate native app. Recommendation:
   Capacitor + Vue + PWA.

---

## 9. Agent operating manual

### 9.1 Read order

1. `AGENTS.md` — repository rules and validation.
2. This roadmap — direction and order.
3. The issue + its comments — scope and acceptance criteria.
4. The relevant code and tests.

### 9.2 Pick work

- Work on **one issue at a time**, from the top of §4.
- Do not skip ahead unless the maintainer says so.
- Do not start an **epic** directly; split it first.
- If the issue has `ai:allowed`, it is eligible. `ai:queued` means it is next.
- If the issue is blocked, ask; do not guess.

### 9.3 Plan and approval

- Post a short plan: what changes, what does not, how it will be tested, risks.
- Wait for maintainer approval before coding.
- If the plan changes after approval, say so before proceeding.

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
- Schema changes: Alembic migration in `backend/migrations/versions/`.
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
- PR description follows the format: `Closes #<issue>`, what changed, validation,
  risk, rollback.

### 9.7 When to stop and ask

- The issue is ambiguous or has no acceptance criteria.
- A change would affect data safety, auth, or another user’s data.
- The work is larger than one PR.
- You need a product decision (§8).
- Tests fail for reasons unrelated to your change.

Use `ai:waiting-for-input` and link the session.

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

---

## 11. Changelog

| Date | Change |
| --- | --- |
| 2026-11-15 | Initial roadmap: Lane A, phase order, mobile and multi-user epics, agent rules |
| 2026-11-15 | Removed `.ai/validate.sh`; added Playwright e2e as UI validation |
| 2026-11-15 | CI: removed Codacy, added path filters/caching/parallel jobs, Docker push on main only |
