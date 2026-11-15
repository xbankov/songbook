#!/usr/bin/env bash
# Run the same checks as CI and .ai-loop.toml.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

isort --check-only backend/app
black --check backend/app
pytest -q backend/app/tests
npm ci --prefix frontend
npm run build --prefix frontend
