# Songbook — agent guide

Bluegrass songbook: FastAPI backend and a Vue 3 frontend, deployed with Docker
Compose.

**Start here:** read [`docs/ROADMAP.md`](docs/ROADMAP.md) for the product
direction, the ordered issue queue, and the rules for splitting epics.

## Validation

The same checks run in CI and in `.ai-loop.toml`. They must exit 0:

```sh
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
isort --check-only backend/app
black --check backend/app
pytest -q backend/app/tests
npm ci --prefix frontend
npm run build --prefix frontend
cd frontend && npx playwright install --with-deps chromium  # first run only
cd frontend && npm run test:e2e
```

## Layout

- `backend/app/` — FastAPI application, SQLAlchemy async models
- `backend/migrations/` — Alembic migrations; deferred until the pre-1.0.0 gate (#69)
- `backend/app/tests/` — pytest suite
- `frontend/src/` — Vue 3 + TypeScript, Vite build

## Rules

- Python: keep type hints, follow the existing black/isort formatting.
- You may edit `.github/` and `docker-compose.yml` when the task requires it;
  explain why in the PR. Never commit `.env` or secrets.
- Do not upgrade dependencies or reformat unrelated files.
- **Single-user first.** Until Phase 6 of the roadmap, assume one user. Do not
  add `users`, `owner_id`, roles, or ownership checks "for later".
- **Pre-1.0.0 schema changes:** do not add Alembic yet (#69 is the pre-1.0.0
  release gate) *unless the database contains data you care about*. `init_db()`
  does not alter existing tables, and resetting a real database deletes the
  library. If real data exists, add the Alembic baseline first:
  fresh DB → `alembic upgrade head`; existing `init_db()` DB → `alembic stamp
  head`, then apply migrations. Never reset a database with real data.
- Frontend changes must keep `npm run build` working; do not commit `dist/`.
- UI changes must keep `npm run test:e2e` working; add a test for user-facing
  behavior.
- Keep pull requests small and focused on one issue.
- Update `docs/ROADMAP.md` in the same PR when the order, scope, or a decision
  changes.

## Implementing an issue

Work only on issues the user asks for in a session (for example "implement
issue #12").

1. Read the issue and its comments. If anything is unclear, ask before coding.
2. Check `docs/ROADMAP.md`: pick one issue from the ordered queue. Do not start
   an epic directly; split it into sub-issues first. Respect the phase order —
   multi-user/data separation is Phase 6, not a prerequisite for single-user work.
3. Briefly state the plan and wait for the user to confirm it.
4. Branch from an up-to-date `main`: `fix/<issue>-<topic>` or `feat/<issue>-<topic>`.
5. Make the change, run the validation above, and fix failures.
6. Commit with a message that references the issue. Never push to `main`.
7. Stop after step 6 and tell the user the branch is ready; the user pushes and
   opens the pull request using the format below.
8. **Wait for the Sourcery review on the latest commit.** Address every finding
   (or reply explaining why it does not apply), push the fixes, and wait for a
   fresh review. Do not call the PR ready until Sourcery has no blocking
   findings and CI is green.

## Review gate

A pull request is ready only when all of these are true:

- CI is green on the **latest** commit.
- Sourcery has reviewed the **latest** commit (not an earlier one).
- Every Sourcery finding is fixed or explicitly answered.
- If a fix changes the code, wait for the next Sourcery review and repeat.

Never merge while a Sourcery finding is unaddressed. Never claim a PR is ready
just because the first CI run passed.

## Pull request format

`Closes #<issue>`, then what changed, how it was validated, risk, rollback, and
**Sourcery: findings addressed / no blocking findings**.
