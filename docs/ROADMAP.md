# Songbook — Roadmap and Agent Guide

> **Status:** living document. Last updated: 2026-11-16.
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
| Separate title/artist fields (#37) | Done in the edit UI; body tags are normalized on export only, not on save |
| Song view: chords above lyrics, styling, 2 columns, autoscroll (#38/#41) | Mostly done |
| Songbooks: CRUD, add/remove, PDF (#24) | Done — delete/rename, reorder, per-entry transpose/columns, TOC; metadata/chordscheme → #89 |
| Import by URL + UG search/pick/import (#46, #51) | Done for UG (parsing fixed in #51) |
| Bulk import (#29) | Partial — paste only; no file/zip upload |
| ChordPro/text/ABC/LilyPond export (#54) | Done — single, selected, all, and per-songbook |
| Print (#55, #56, #57, #58, #59) | Done — single/selected/songbook, 1/2-column long-song layout, chords above lyrics, margins/headings/page numbers |
| Library pagination (#27) | Done |
| Version rows + list/get APIs (#45) | Done — history + restore; authors/forks/favourites/permalink split to #88 |
| Audio record/upload/playback (#42) | Partial — no record mode/privacy |
| Tags model + API filter (#26) | Done — tag-based difficulty/genre filters, alphabet, badges |
| Auth (#68) | Done — every API router depends on `require_auth` |
| Migrations | Deferred for dev/empty DBs — add the Alembic baseline (#69) before changing a schema under real data, and at the pre-1.0.0 gate |

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
| AI lab (parked) | LLM parsing, annotations, translations, recommendations | #34, #1, #36, #40, #39, #35, #62, #49, #53 |
| Operations | Domain, deployment, backups | #22 |
| Pre-1.0.0 release gate | Alembic baseline, backup/restore, export/import, e2e | #69 |

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

> **Alembic (#69) is deferred for dev/empty databases.** `init_db()` is acceptable
> while there is no data you care about. If a schema change must preserve a real
> library, add the baseline first. Existing `init_db()` databases must be
> `alembic stamp`ed at the baseline, not recreated; resetting a real database
> deletes it.

### Phase 1 — Library and songbooks

**Status:** #26, #27, #24, #45 done; only #89 remains (blocked on a storage
decision, §8).

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 6 | #26 Filter by difficulty/genre/artist/alphabet | M | A growing songbook needs retrieval |
| 7 | #27 Pagination | M | The UI currently shows at most 50 songs |
| 8 | #24 Songbook completion (TOC, sorting, per-entry settings, delete/rename) | L | The songbook is the core artifact |
| 9a | #89 Songbook metadata + chord-scheme selection | M | Needs a schema decision/Alembic first |
| 9 | #45 Version history UI + restore (authors/forks/favourites → #88) | M | Editing must be safe |

**Resolved:** #26 stores difficulty and genre as tags (`difficulty:*`,
`genre:*`); #27 can build pagination on the same filters.

### Phase 2 — Print and export

**Status:** #54, #56, #57, #58 done (plus #55, #59); only #44 remains (needs a
spec for "starting note" and "rhythmic pattern"; `capo`/`key` already exist).

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 10 | #54 Download ChordPro for one/selected/all | S | Data ownership; also feeds #28 |
| 11 | #56 Print buttons (single/selected/book) | M | The main workflow |
| 12 | #57 Chord signs in print/PDF | S | Chords should look like chords |
| 13 | #58 Print looks (margins, headings, page numbers) | S | Polish |
| 14 | #44 Expand ChordPro tags | S | Starting note/rhythm are the only gaps |

### Phase 3 — Import ecosystem

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 15 | #29 Batch upload (clarify paste vs file/zip) | M | Bring an existing library in at once |
| 16 | #50 Import pisnicky-akordy.cz | M | The other site this circle uses |
| 17 | #20 Harden Supermusic import | M | Existing generic parser needs fixtures |
| 18 | #46 Direct lookup by name (narrow to extra sources) | S | UG flow already exists |
| 19 | #28 Import/export a Git repo | L | Data ownership and versioned backups |

**Not scheduled — #78 catalog & acquisition epic ("Lidarr for chord sheets").**
A MusicBrainz-backed metadata catalog plus a reviewable acquisition queue. It is a
design epic: resolve its open decisions (§8) and split it (§9.4) before any code.
The issue itself recommends starting only after the Alembic baseline (#69).

### Phase 4 — Performance mode

| # | Issue | Size | Why |
| --- | --- | --- | --- |
| 20 | #41 Play/sing view (full-screen, current-line highlight) | M | Rehearsal/gig use |
| 21 | #42 + #43 Recordings/attachments (merge) | L | Useful, but larger |
| 22 | #25 YouTube link | S | Small reference feature |

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
#62 recommendations → #49 auto-transcribe → #53 LLM parsing.

Treat these as experiments: time-boxed, behind a flag if possible, and never on
the critical path.

### Phase 8 — Operations

#22 Custom domain + TLS. This is an ops checklist, not application code.

### Pre-1.0.0 release gate

Do these before tagging 1.0.0:

- #69 Add the Alembic baseline. Test both upgrade paths:
  - fresh database: `alembic upgrade head`
  - existing `init_db()` database: `alembic stamp head`, then upgrade
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

Still open on GitHub (as of 2026-11-16) and ready to close by hand:

- #2 Transposition — implemented.
- #38 Improve song view — print parity was the remaining work; done in #57.
- #61 SongBook vs UG — answered by §1 (Lane A); close with a link here.

Not yet: #60 (where lyrics come from) stays open until the import policy (§8.7)
is written down.

Still open; needs a small follow-up first:

- #37 Title/artist outside lyrics — body tags are normalized on export only;
  normalize on save too, then close.
- #46 Direct lookup by name — UG flow exists; narrow the issue to extra sources.

Closed: #15 (regression test added), #33 (re-triaged).

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
9. **#89 songbook metadata storage (blocking #89).** New `songbooks` columns vs.
   one metadata JSON column. Columns require the Alembic baseline (#69) first if
   the database holds a real library; a JSON column still changes the schema.
10. **#78 catalog & acquisition (blocking #78).** Approve the catalog / library /
    acquisition model; MusicBrainz work/recording MBIDs as canonical identity;
    the source policy (UG manual-only, no public chord catalog); whether to retire
    `backend/crawler.py` bulk import; and the first slice to build.

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

### 9.3.1 Review gate (Sourcery)

A PR is never “ready” after the first CI run. It must pass this gate:

- CI is green on the **latest** commit.
- Sourcery has reviewed the **latest** commit.
- Every Sourcery finding is fixed, or explicitly answered with a reason.
- Push the fixes and wait for a fresh review; repeat until no blocking findings.

If a Sourcery finding is unclear, ask the maintainer. Do not ignore, dismiss, or
silently skip it.

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
- **Schema changes:** for dev/empty databases, `init_db()` is acceptable pre-1.0.0.
  If the database contains data you care about, add the Alembic baseline first
  (#69) and migrate. Never reset a real database. Existing `init_db()` databases
  are stamped at the baseline, not recreated.
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
| 2026-11-15 | Every PR waits for the Sourcery review on the latest commit and addresses all findings before it is ready or merged | @xbankov |
| 2026-11-15 | Single-user functionality first; multi-user/data separation is a later layer (Phase 6), started only when the single-user product is liked | @xbankov |
| 2026-11-15 | Alembic is deferred for dev/empty databases; it is required before changing a schema under real data and at the pre-1.0.0 release gate. Never reset a real database | @xbankov |
| 2026-11-15 | Difficulty and genre use tags (`difficulty:*`, `genre:*`); no new columns (#26) | @xbankov |
| 2026-11-15 | Version history/restore ships now; version authors, forking, favourites, and permalinks are deferred to #88 with multi-user | @xbankov |
| 2026-11-15 | Songbook core (delete/rename, reorder, per-entry settings, TOC) ships now; metadata/chordscheme split to #89 pending a schema decision | @xbankov |
| 2026-11-15 | Long-song print layout is configurable (1/2 columns), not forced to one column (#55) | @xbankov (via #84) |

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
