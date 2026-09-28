# CLAUDE.md — Estudio Virtual (Santiago Muebles)

Eres el agente de desarrollo de este repo. La dueña es **Gabriela**.

## Antes de cualquier cosa
1. Lee `PLAN.md` completo (fuente de verdad) y `PROGRESO.md` (dónde vamos).
2. Continúa en la **primera tarea sin marcar** de `PROGRESO.md`. No saltes tareas ni fases.
3. En cada 🛑 del plan: detente, reporta con el formato de PLAN §8 y espera respuesta.

## Reglas
- Costo $0: nada pago, nada que pida tarjeta. Solo licencias MIT/Apache/BSD/CC0/CC-BY (PLAN §0.7). Si dudas, pregunta.
- UI, mensajes y documentación en español. Código e identificadores en inglés.
- Coordenadas: sigue PLAN §4 al pie de la letra. Conversión OpenCV→three solo en `backend/app/geometry/coords.py`.
- Secretos solo en `.env` (nunca en git). Mantén `.env.example` al día.
- Tras cada tarea: verificar → actualizar `PROGRESO.md` → `git commit -m "fase X.Y: ..."`.
- Mismo error 2 veces con enfoques distintos → para y pregunta.
- No refactorices fuera del alcance de la tarea. Archivos < ~400 líneas.
- Para verificar UI: corre Playwright, guarda capturas en `frontend/test-results/` y **ábrelas y míralas** (Read) antes de dar algo por bueno.

## Comandos
| Qué | Comando |
|---|---|
| Instalar deps backend | `cd backend && uv sync` |
| Tests backend (rápidos) | `cd backend && uv run pytest -q -m "not slow"` |
| Tests backend (con modelos) | `cd backend && uv run pytest -q -m slow` |
| Servidor backend (dev) | `cd backend && uv run uvicorn app.main:app --reload --port 8000` |
| Frontend dev | `cd frontend && npm run dev` (proxy a :8000) |
| Tests frontend | `cd frontend && npm run test` |
| e2e | `cd frontend && npx playwright test` (instalar navegador una vez: `npx playwright install chromium`) |
| Build servido por FastAPI | `bash scripts/build_frontend.sh` |
| App completa como usuario final | `bash scripts/mac/iniciar.command` → http://localhost:8000 |
| Release para compartir | `bash scripts/crear_release.sh` |
| Lint | `cd backend && uv run ruff check .` · `cd frontend && npm run lint` |

## Datos de prueba
- `samples/rooms/` fotos del apartamento (+ `medidas_reales.json` opcional), `samples/videos/` videos.
- `samples/furniture/<mueble>/` = `foto*.jpg` + `medidas.*` (captura de la tabla de la tienda). Tú lees la tabla y creas
  `mueble.json` (PLAN tarea 0.6, esquema y definición de ancho/fondo/alto en PLAN §5.2).
- Las medidas de los muebles son la fuente de verdad de la escala: todo mueble se muestra a su tamaño real en cm.
- Son datos de Gabriela: no los borres ni los subas a servicios externos (salvo el retoque IA que ella active).
  Las fotos de tiendas son solo para pruebas internas.
