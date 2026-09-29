#!/usr/bin/env bash
# Abre el Estudio Virtual en http://localhost:8000
cd "$(dirname "$0")/../.." || exit 1
export PATH="$HOME/.local/bin:$PATH"  # donde queda uv si lo instaló instalar.command

if ! command -v uv >/dev/null 2>&1; then
  echo "Falta 'uv'. Primero haz doble clic en scripts/mac/instalar.command"
  echo "Presiona Enter para cerrar."
  read -r _
  exit 1
fi

uv run --directory backend python -m app.run
status=$?
if [ $status -ne 0 ]; then
  echo ""
  echo "La app se cerró con un error (código $status). Presiona Enter para cerrar."
  read -r _
fi
exit $status
