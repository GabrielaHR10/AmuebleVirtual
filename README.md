# Estudio Virtual — Santiago Muebles

Sube una foto (o un video) de un espacio, elige muebles reales del catálogo y mira el espacio
amoblado **a escala real**, con sombras y sugerencias de ubicación. Todo corre en tu computador,
en `http://localhost:8000`, sin costo.

## Cómo arrancar
- **Mac:** `scripts/mac/instalar.command` (la primera vez) y luego `scripts/mac/iniciar.command`
  (clic derecho → Abrir).
- **Windows:** `scripts\windows\instalar.bat` (la primera vez) y luego `scripts\windows\iniciar.bat`.

La primera vez se instala todo lo necesario (Python, librerías y modelos de IA, ~2–3 GB); luego se abre
el navegador.

## Qué hace
- **Estudio:** analiza la foto (piso, altura de la cámara, medidas aproximadas del espacio), pone los muebles
  a su tamaño real con sombras y oclusión, avisa si no caben, sugiere dónde ubicarlos y exporta un PNG.
  "Calibrar medida" corrige la escala si conoces una distancia real.
- **Video:** elige los fotogramas nítidos de un recorrido donde se ve el piso, para amoblarlos como fotos.
- **Catálogo:** muebles con sus medidas en cm. Se agregan con una foto de frente (se quita el fondo sola);
  con la IA local opcional se leen las medidas desde la foto de la tabla de la tienda.

## IA local opcional
Para leer tablas de medidas: instala [Ollama](https://ollama.com) y corre `ollama pull qwen3-vl:4b-instruct`.

## Para desarrollo
Comandos en [`CLAUDE.md`](CLAUDE.md); verificación completa con `bash scripts/verificar.sh`;
release con `bash scripts/crear_release.sh`. Avance en [`PROGRESO.md`](PROGRESO.md) y plan en [`PLAN.md`](PLAN.md).
Licencias de modelos y assets en [`THIRD_PARTY.md`](THIRD_PARTY.md).
