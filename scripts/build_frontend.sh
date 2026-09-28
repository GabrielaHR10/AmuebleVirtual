#!/usr/bin/env bash
# Compila el frontend y lo copia a backend/app/static para que FastAPI lo sirva en /
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATIC="$ROOT/backend/app/static"

cd "$ROOT/frontend"
npm ci
npm run build

rm -rf "$STATIC"
mkdir -p "$STATIC"
cp -R dist/. "$STATIC/"
echo "Frontend compilado en $STATIC"
