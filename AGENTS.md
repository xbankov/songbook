# Songbook — agent guide

Bluegrass songbook: FastAPI backend and a Vue 3 frontend, deployed with Docker
Compose.

**Start here:** read [`docs/ROADMAP.md`](docs/ROADMAP.md) for the product
direction, the ordered issue queue, and the rules for splitting epics.

## Validation

CI (`.github/workflows/system.yaml`) runs these same checks, skipping jobs
whose paths did not change. They must exit 0:

```sh
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
isort --check-only backend/app
black --check backend/app
pytest -q backend/app/tests  # set MIGRATION_TEST_DATABASE_URL to a throwaway
                             # Postgres to also run the migration tests
npm ci --prefix frontend
npm run build --prefix frontend
cd frontend && npx playwright install --with-deps chromium  # first run only
cd frontend && npm run test:e2e
```

## Layout

- `backend/app/` — FastAPI application, SQLAlchemy async models
- `backend/migrations/` — Alembic migrations (applied at startup by `app/migrate.py`)
- `backend/app/tests/` — pytest suite
- `frontend/src/` — Vue 3 + TypeScript, Vite build

## Rules

- Python: keep type hints, follow the existing black/isort formatting.
- You may edit `.github/` and `docker-compose.yml` when the task requires it;
  explain why in the PR. Never commit `.env` or secrets.
- Do not upgrade dependencies or reformat unrelated files.
- **Single-user first.** Until Phase 6 of the roadmap, assume one user. Do not
  add `users`, `owner_id`, roles, or ownership checks "for later".
- **Schema changes need an Alembic migration.** Change the model, then run
  `alembic revision --autogenerate -m "<change>"` in `backend/` against a dev
  database, review the file, and commit it. Migrations must preserve data (the
  running instance holds a real library) and must downgrade. The backend
  migrates on startup (`app/migrate.py`); never reset a database with real data.
- Frontend changes must keep `npm run build` working; do not commit `dist/`.
- UI changes must keep `npm run test:e2e` working; add a test for user-facing
  behavior.
- Keep pull requests small and focused on one issue.
- Update `docs/ROADMAP.md` in the same PR when the order, scope, or a decision
  changes.

## Implementing an issue

Work only on issues the user asks for in a session (for example "implement
issue #12"). Do not pick issues yourself.

1. Read the issue and its comments. If anything is unclear, ask before coding.
2. Check the issue against `docs/ROADMAP.md` §4. If it is out of queue order or
   blocked, say so and let the user decide. Do not start an epic directly;
   split it into sub-issues first. Respect the phase order — multi-user/data
   separation is Phase 6, not a prerequisite for single-user work.
3. Briefly state the plan and wait for the user to confirm it.
4. Branch from an up-to-date `main`: `fix/<issue>-<topic>` or `feat/<issue>-<topic>`.
5. Make the change, run the validation above, and fix failures.
6. Commit with a message that references the issue. Never push to `main`.
7. Stop and tell the user the branch is ready. The user pushes and opens the
   pull request using the format below.

## Addressing review

When the user asks you to handle review on an open pull request:

1. Read the Sourcery review on the **latest** commit and every inline comment.
2. Fix each finding on the PR branch, or reply to it explaining why it does
   not apply.
3. Run the validation above and commit the fixes.
4. Push only when the user asks; then wait for a fresh Sourcery review and
   repeat. Do not call the PR ready until Sourcery has no blocking findings
   and CI is green.

## Review gate

A pull request is ready only when all of these are true:

- CI is green on the **latest** commit.
- Sourcery has reviewed the **latest** commit (not an earlier one).
- Every Sourcery finding is fixed or explicitly answered.
- If a fix changes the code, wait for the next Sourcery review and repeat.

Never merge while a Sourcery finding is unaddressed. Never claim a PR is ready
just because the first CI run passed.

**Exception — Dependabot minor/patch PRs** merge themselves: `dependabot-automerge.yml`
enables auto-merge, and GitHub merges once the required checks "CI passed" and
"Sourcery review" succeed. A Dependabot PR with failing CI stays open; fix it
like any other PR. Major updates are never auto-merged; review them by hand.

## Pull request format

`Closes #<issue>`, then what changed, how it was validated, risk, rollback, and
**Sourcery: findings addressed / no blocking findings**.
