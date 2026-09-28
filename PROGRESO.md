# Progreso — Estudio Virtual
Versión actual: 0.0.0 · Última actualización: 2026-09-28

## Fase 0
- [x] 0.1 Repo y documentos base — nota: estructura de §3 con `.gitkeep`, `.gitignore`, `.env.example`, `THIRD_PARTY.md`, `README.md`. `frontend/` se crea en 0.3 (Vite exige carpeta nueva).
- [x] 0.2 Backend mínimo — nota: FastAPI con `/api/health`, `/files` y SPA desde `app/static`. `app.run` avisa en español si el puerto 8000 está ocupado; `NO_BROWSER=1` evita abrir el navegador (CI/pruebas). uv 0.12 crea layout `src/` con `uv init`: se reemplazó por `pyproject.toml` con `package = false`.
- [x] 0.3 Frontend mínimo — nota: Vite 8 + React 19 + TS strict + three/R3F/drei + zustand + Tailwind 4; proxy `/api` y `/files`. e2e `e2e/home.spec.ts` → `frontend/test-results/home.png` (revisada: título, "Servidor conectado", cubo). Hizo falta `preserveDrawingBuffer: true` para que la captura muestre el WebGL. Lint del template es `oxlint` (MIT).
- [x] 0.4 Scripts de instalación/arranque — nota: `scripts/mac/*.command` y `scripts/windows/*.bat`. En Mac, `instalar` además compila la interfaz si falta (repo clonado). Probado en Mac con `NO_BROWSER=1` desde otra carpeta: health OK. `.gitattributes` fuerza CRLF en `.bat`. Doble clic real: pendiente que Gabriela lo confirme.
- [x] 0.5 CI de humo en Windows — nota: `.github/workflows/smoke.yml` (windows-latest + macos-14): uv sync, pytest, `instalar.bat`/`iniciar.bat` (o `iniciar.command`) y health. Run 36490331645 verde en ambos. setup-uv no publica etiqueta `v10`: fijado a `v10.2.0`.
- [x] 0.6 Catálogo de medidas desde las carpetas de Gabriela — nota: 3 `mueble.json` + `RESUMEN_MEDIDAS.md`; `FurnitureSpec` en `schemas.py` y `tests/test_furniture_specs.py`. Mesa Gretel ambigua (ancho vs. fondo) → se pregunta en el 🛑.
- [x] 🛑 Fin Fase 0: revisión con Gabriela — nota: la app le abrió en su Mac (ve el cubo). Mesa Gretel verificada. Sofás: sin respuesta todavía, quedan `dimensions_verified: false`.

## Fase 1
- [ ] 1.1 Ejecutar MoGe-2 — nota:
- [ ] 1.2 Conversiones y utilidades (coords.py) — nota:
- [ ] 1.3 Detección del piso — nota:
- [ ] 1.4 Malla de oclusión — nota:
- [ ] 1.5 Endpoint POST /api/scenes — nota:
- [ ] 1.6 Precarga de modelos — nota:
- [ ] 1.7 Dimensionar el espacio — nota:
- [ ] 🛑 Fin Fase 1

## Fase 2
- [ ] 2.1 Catálogo: servicio y endpoints — nota:
- [ ] 2.2a Importar los muebles de Gabriela — nota:
- [ ] 2.2b Catálogo complementario Poly Haven — nota:
- [ ] 2.3 Miniaturas — nota:
- [ ] 2.4 HDRI de iluminación — nota:
- [ ] 2.5 Muebles propios desde foto (recorte 2D) — nota:
- [ ] 2.6 Editor 3D: estructura de capas — nota:
- [ ] 2.7 Muebles en el editor — nota:
- [ ] 2.8 Calibración de escala — nota:
- [ ] 2.9 Piso manual — nota:
- [ ] 2.10 Exportar PNG — nota:
- [ ] 2.11 UI general (PhotoStudio) — nota:
- [ ] 🛑 Fin Fase 2

## Fase 3
- [ ] 3.1 Grilla de ocupación — nota:
- [ ] 3.2 Heurística — nota:
- [ ] 3.3 VLM local opcional — nota:
- [ ] 3.4 UI — nota:
- [ ] 3.5 Tests — nota:
- [ ] 3.6 Leer tabla de medidas automáticamente — nota:
- [ ] 🛑 Fin Fase 3

## Fase 4
- [ ] 4.1 Retoque clásico — nota:
- [ ] 4.2 Proveedor IA — nota:
- [ ] 4.3 UI — nota:
- [ ] 🛑 Fin Fase 4

## Fase 5
- [ ] 5.1 Video a fotogramas clave — nota:
- [ ] 🛑 Tras 5.1
- [ ] 5.2 Seguimiento de cámara (SfM) — nota:
- [ ] 5.3 Render del video — nota:
- [ ] 🛑 Tras 5.3

## Fase 6
- [ ] 6.1 Proveedor foto→3D — nota:
- [ ] 6.2 Normalización — nota:
- [ ] 6.3 UI — nota:
- [ ] 🛑 Fin Fase 6

## Fase 7
- [ ] 7.1 Release zip — nota:
- [ ] 7.2 Demo en vivo temporal (opcional) — nota:

## Decisiones tomadas con Gabriela
- 2026-09-28: Mesa Gretel se deja como dice la tabla: frente (width) 80 cm, fondo (depth) 140 cm (opción B).
- 2026-09-28: la app arranca en el Mac de Gabriela con doble clic.

## Problemas abiertos
- Medidas de los dos sofás (Edingburgh y click-clack) pendientes de confirmar por Gabriela.

## Mediciones
| Foto | Dispositivo | Tiempo análisis | Altura cámara | % piso |
|---|---|---|---|---|
