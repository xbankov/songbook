# Songbook — agent guide

Bluegrass songbook: FastAPI backend and a Vue 3 frontend, deployed with Docker
Compose.

## Validation

```sh
./.ai/validate.sh
```

It runs, in a Python 3.12 container: `pip install`, `isort --check-only`,
`black --check`, `pytest -q backend/src`. It must exit 0.

## Layout

- `backend/app/` — FastAPI application, SQLAlchemy async models
- `backend/migrations/` — Alembic migrations; add one when models change
- `backend/tests/` — pytest suite
- `frontend/src/` — Vue 3 + TypeScript, Vite build

## Rules

- Python: keep type hints, follow the existing black/isort formatting.
- Never edit `.github/`, `.env`, or `docker-compose.yaml`.
- Do not upgrade dependencies or reformat unrelated files.
- Schema changes need an Alembic migration in `backend/migrations/versions/`.
- Frontend changes must keep `npm run build` working; do not commit `dist/`.
- Keep pull requests small and focused on one issue.

## Implementing an issue

Work only when the user asks in a session (for example "implement issue #12").
There is no automatic agent.

1. Read the issue and its comments. If anything is unclear, ask before coding.
2. Briefly state the plan and wait for the user to confirm it.
3. Branch from an up-to-date `main`: `fix/<issue>-<topic>` or `feat/<issue>-<topic>`.
4. Make the change, run the validation above, and fix failures.
5. Commit with a message that references the issue. Never push to `main`.
6. Stop and tell the user the branch is ready; the user pushes and opens the
   pull request using the format below.

## Pull request format

`Closes #<issue>`, then what changed, how it was validated, risk, rollback.
