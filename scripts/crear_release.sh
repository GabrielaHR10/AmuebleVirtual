#!/usr/bin/env bash
# Arma release/santiago-muebles-v<versión>.zip para compartir (PLAN 7.1).
# Copia SOLO los archivos del repositorio (git ls-files) + la interfaz compilada (backend/app/static).
# Sin frontend/ (ya va compilado), samples/, .env, escenas ni documentos internos del agente.
# Por defecto NO incluye los muebles con fotos de tiendas ("solo pruebas internas"); --con-fotos-de-tienda los incluye.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_STORE=0
[ "${1:-}" = "--con-fotos-de-tienda" ] && WITH_STORE=1

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' backend/app/__init__.py)"
NAME="santiago-muebles-v${VERSION}"
OUT="release/${NAME}"

echo "→ Compilando la interfaz…"
bash scripts/build_frontend.sh > /dev/null

echo "→ Copiando archivos a ${OUT}…"
rm -rf "$OUT" "release/${NAME}.zip"
mkdir -p "$OUT"
git ls-files -z \
  | grep -zv -e '^frontend/' -e '^samples/' -e '^\.github/' -e '^\.claude/' \
             -e '^CLAUDE\.md$' -e '^PLAN\.md$' -e '^PROGRESO\.md$' -e '^backend/tests/' \
  | rsync -a --from0 --files-from=- ./ "$OUT/"
rsync -a backend/app/static/ "$OUT/backend/app/static/"

if [ "$WITH_STORE" = "0" ]; then
  echo "→ Quitando los muebles con fotos de tiendas (solo pruebas internas)…"
  python3 - "$OUT/data/catalog" <<'PY'
import json, shutil, sys
from pathlib import Path
cat = Path(sys.argv[1])
kept = []
for spec in sorted(cat.glob("*/mueble.json")):
    item = json.loads(spec.read_text(encoding="utf-8"))
    if item.get("license") == "solo pruebas internas":
        shutil.rmtree(spec.parent)
    else:
        kept.append(item)
(cat / "catalog.json").write_text(json.dumps({"items": kept}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"   quedan {len(kept)} muebles")
PY
fi

cat > "$OUT/LEEME_PRIMERO.txt" <<'EOF'
ESTUDIO VIRTUAL — SANTIAGO MUEBLES
==================================

1. Descomprime esta carpeta donde quieras (por ejemplo en Documentos).

2. Instala (solo la primera vez):
   - WINDOWS: doble clic en  scripts\windows\instalar.bat
     Si aparece "Windows protegió su PC": clic en "Más información" → "Ejecutar de todas formas".
   - MAC: clic derecho en  scripts/mac/instalar.command → Abrir → Abrir.

   La primera vez se descarga lo necesario (Python, librerías y modelos de IA, ~2–3 GB).
   Puede tardar entre 5 y 15 minutos. Si se corta, vuelve a abrir el instalador: no se pierde lo descargado.

3. Abre la app:
   - WINDOWS: doble clic en  scripts\windows\iniciar.bat
   - MAC: clic derecho en  scripts/mac/iniciar.command → Abrir
   Se abre el navegador en  http://localhost:8000

4. Cómo se usa:
   - Pestaña "Estudio": sube una foto del espacio (JPG o PNG), agrega muebles del catálogo,
     usa "Sugerir ubicación" y exporta la imagen con "Exportar PNG".
   - Pestaña "Video": sube un recorrido y amobla sus fotogramas.
   - Pestaña "Catálogo": agrega muebles propios (foto de frente + medidas en cm).

5. Para cerrar la app, cierra la ventana negra (la consola).

6. Opcional — IA local para leer las tablas de medidas de las tiendas (gratis, en tu computador):
   instala Ollama desde https://ollama.com y luego, en una terminal:  ollama pull qwen3-vl:4b-instruct
EOF

echo "→ Comprimiendo…"
(cd release && zip -qr "${NAME}.zip" "${NAME}")
echo "Listo: release/${NAME}.zip ($(du -h "release/${NAME}.zip" | cut -f1))"
