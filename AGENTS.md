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
- `backend/migrations/` — Alembic migrations; add one when models change
- `backend/app/tests/` — pytest suite
- `frontend/src/` — Vue 3 + TypeScript, Vite build

## Rules

- Python: keep type hints, follow the existing black/isort formatting.
- You may edit `.github/` and `docker-compose.yml` when the task requires it;
  explain why in the PR. Never commit `.env` or secrets.
- Do not upgrade dependencies or reformat unrelated files.
- Schema changes need an Alembic migration in `backend/migrations/versions/`.
- Frontend changes must keep `npm run build` working; do not commit `dist/`.
- UI changes must keep `npm run test:e2e` working; add a test for user-facing
  behavior.
- Keep pull requests small and focused on one issue.
- Update `docs/ROADMAP.md` in the same PR when the order, scope, or a decision
  changes.

## Implementing an issue

Work only on issues a maintainer allows: the AI maintainer picks up issues
labelled `ai:allowed` (see README), or the user asks in a session (for example
"implement issue #12").

1. Read the issue and its comments. If anything is unclear, ask before coding.
2. Check `docs/ROADMAP.md`: pick one issue from the ordered queue. Do not start
   an epic directly; split it into sub-issues first.
3. Briefly state the plan and wait for the user to confirm it.
4. Branch from an up-to-date `main`: `fix/<issue>-<topic>` or `feat/<issue>-<topic>`.
5. Make the change, run the validation above, and fix failures.
6. Commit with a message that references the issue. Never push to `main`.
7. The AI maintainer pushes the branch, opens the pull request using the format
   below, and waits for CI. In a manual session, stop after step 6 and tell the
   user the branch is ready; the user pushes and opens the pull request.

## Pull request format

`Closes #<issue>`, then what changed, how it was validated, risk, rollback.
