#!/usr/bin/env bash
# Corre lint y todas las pruebas rápidas; se detiene en el primer error (usar antes de cada commit).
# E2E_PORT (default 8001) evita chocar con la app abierta en el 8000. SIN_E2E=1 salta Playwright.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== backend: ruff + pytest"
(cd "$ROOT/backend" && uv run ruff check . && uv run pytest -q -m "not slow")

echo "== frontend: lint + vitest + build"
(cd "$ROOT/frontend" && npm run lint --silent >/dev/null && npx vitest run && npx tsc -b)
bash "$ROOT/scripts/build_frontend.sh" > /dev/null

if [ "${SIN_E2E:-}" != "1" ]; then
  echo "== e2e: playwright"
  (cd "$ROOT/frontend" && E2E_PORT="${E2E_PORT:-8001}" npx playwright test --reporter=line)
fi
echo "OK: todo verificado"
