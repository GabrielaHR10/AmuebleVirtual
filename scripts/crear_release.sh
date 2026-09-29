#!/usr/bin/env bash
# Arma release/santiago-muebles-v<versión>.zip para compartir (PLAN 7.1).
# Incluye el frontend ya compilado en backend/app/static; no incluye node_modules, .venv, escenas, .env ni samples/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' backend/app/__init__.py)"
NAME="santiago-muebles-v${VERSION}"
OUT="release/${NAME}"

echo "→ Compilando la interfaz…"
bash scripts/build_frontend.sh > /dev/null

echo "→ Copiando archivos a ${OUT}…"
rm -rf "$OUT" "release/${NAME}.zip"
mkdir -p "$OUT"
rsync -a \
  --exclude '.git' --exclude '.github' --exclude '.claude' --exclude '.DS_Store' \
  --exclude 'node_modules' --exclude 'frontend/' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.pytest_cache' --exclude '.ruff_cache' \
  --exclude 'data/scenes/*' --exclude 'data/videos/*' --exclude 'data/catalog/*/thumb_512.png' \
  --exclude '.env' --exclude 'samples/' --exclude 'release/' \
  --exclude 'CLAUDE.md' --exclude 'PLAN.md' --exclude 'PROGRESO.md' \
  ./ "$OUT/"

cat > "$OUT/LEEME_PRIMERO.txt" <<'EOF'
ESTUDIO VIRTUAL — SANTIAGO MUEBLES
==================================

1. Descomprime esta carpeta donde quieras (por ejemplo en Documentos).

2. Abre la app:
   - WINDOWS: doble clic en  scripts\windows\instalar.bat  (solo la primera vez)
     y luego en  scripts\windows\iniciar.bat
     Si aparece "Windows protegió su PC": clic en "Más información" → "Ejecutar de todas formas".
   - MAC: clic derecho en  scripts/mac/instalar.command → Abrir  (solo la primera vez)
     y luego clic derecho en  scripts/mac/iniciar.command → Abrir.
     (En Mac hace falta tener "uv": en la Terminal escribe  brew install uv )

3. La primera vez se descarga lo necesario (Python, librerías y modelos de IA, ~2–3 GB).
   Puede tardar entre 5 y 15 minutos. Si se corta, vuelve a abrir el instalador: no se pierde lo descargado.

4. Se abre el navegador en  http://localhost:8000
   Sube una foto del espacio (JPG o PNG), agrega muebles del catálogo y exporta la imagen.

5. Para cerrar la app, cierra la ventana negra (la consola).

6. Opcional — retoque con IA: crea un token gratis en https://huggingface.co/settings/tokens,
   copia el archivo .env.example como .env y pega el token en HF_TOKEN=.

Las fotos de muebles de tiendas incluidas son solo para pruebas internas: no las publiques.
EOF

echo "→ Comprimiendo…"
(cd release && zip -qr "${NAME}.zip" "${NAME}")
echo "Listo: release/${NAME}.zip ($(du -h "release/${NAME}.zip" | cut -f1))"
