#!/usr/bin/env bash
# Instala todo lo necesario para el Estudio Virtual en Mac. Se puede correr varias veces.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

fail() {
  echo ""
  echo "ERROR: $1"
  echo "Presiona Enter para cerrar."
  read -r _
  exit 1
}

echo "=== Estudio Virtual — instalación ==="

if ! command -v uv >/dev/null 2>&1; then
  echo ""
  echo "Falta 'uv' (el instalador de Python)."
  echo "Instálalo con Homebrew abriendo la Terminal y escribiendo:"
  echo ""
  echo "    brew install uv"
  echo ""
  echo "(Si no tienes Homebrew: https://brew.sh)  Luego vuelve a abrir este instalador."
  fail "uv no está instalado."
fi

echo "→ Instalando Python y librerías (la primera vez puede tardar varios minutos)…"
(cd backend && uv sync) || fail "No se pudieron instalar las librerías. Revisa tu conexión a internet y vuelve a intentar."

echo "→ Descargando modelos de IA…"
(cd backend && uv run python -m app.prefetch) || fail "No se pudieron descargar los modelos. Revisa tu conexión y vuelve a intentar."

# Si se clonó el repo (no el release), compilar la interfaz cuando falte
if [ ! -f backend/app/static/index.html ] && [ -d frontend ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "→ Compilando la interfaz…"
    bash scripts/build_frontend.sh || fail "No se pudo compilar la interfaz."
  else
    echo "Aviso: falta la interfaz compilada y no hay Node.js (npm). Instálalo con: brew install node"
  fi
fi

echo ""
echo "Listo. Para abrir la app: doble clic en scripts/mac/iniciar.command"
