# Progreso — Estudio Virtual
Versión actual: 0.2.0 · Última actualización: 2026-09-28

## Fase 0
- [x] 0.1 Repo y documentos base — nota: estructura de §3 con `.gitkeep`, `.gitignore`, `.env.example`, `THIRD_PARTY.md`, `README.md`. `frontend/` se crea en 0.3 (Vite exige carpeta nueva).
- [x] 0.2 Backend mínimo — nota: FastAPI con `/api/health`, `/files` y SPA desde `app/static`. `app.run` avisa en español si el puerto 8000 está ocupado; `NO_BROWSER=1` evita abrir el navegador (CI/pruebas). uv 0.12 crea layout `src/` con `uv init`: se reemplazó por `pyproject.toml` con `package = false`.
- [x] 0.3 Frontend mínimo — nota: Vite 8 + React 19 + TS strict + three/R3F/drei + zustand + Tailwind 4; proxy `/api` y `/files`. e2e `e2e/home.spec.ts` → `frontend/test-results/home.png` (revisada: título, "Servidor conectado", cubo). Hizo falta `preserveDrawingBuffer: true` para que la captura muestre el WebGL. Lint del template es `oxlint` (MIT).
- [x] 0.4 Scripts de instalación/arranque — nota: `scripts/mac/*.command` y `scripts/windows/*.bat`. En Mac, `instalar` además compila la interfaz si falta (repo clonado). Probado en Mac con `NO_BROWSER=1` desde otra carpeta: health OK. `.gitattributes` fuerza CRLF en `.bat`. Doble clic real: pendiente que Gabriela lo confirme.
- [x] 0.5 CI de humo en Windows — nota: `.github/workflows/smoke.yml` (windows-latest + macos-14): uv sync, pytest, `instalar.bat`/`iniciar.bat` (o `iniciar.command`) y health. Run 36490331645 verde en ambos. setup-uv no publica etiqueta `v10`: fijado a `v10.2.0`.
- [x] 0.6 Catálogo de medidas desde las carpetas de Gabriela — nota: 3 `mueble.json` + `RESUMEN_MEDIDAS.md`; `FurnitureSpec` en `schemas.py` y `tests/test_furniture_specs.py`. Mesa Gretel ambigua (ancho vs. fondo) → se pregunta en el 🛑.
- [x] 🛑 Fin Fase 0: revisión con Gabriela — nota: la app le abrió en su Mac (ve el cubo). Mesa Gretel verificada. Sofás: sin respuesta todavía, quedan `dimensions_verified: false`.

## Fase 1
- [x] 1.1 Ejecutar MoGe-2 — nota: `moge_runner.py` + `scripts/probe_moge.py` sobre las 14 fotos. **MPS**, ~0.94 s/foto (1024 px), carga del modelo ~2.7 s. Intrínsecos **normalizados** (cx = cy = 0.500), fov_y 60–72°. MoGe `main` ya es V3 (exige flex-gemm/CUDA, sin macOS) → fijado al commit `925b8ed` (MoGe-2). `gradio` y `opencv-python` excluidos por override. `pillow-heif` quitado (GPLv2) → HEIC rechazado con mensaje; pendiente preguntar. Foto `10.04.08 (8)` es vista por la ventana (no es cuarto).
- [x] 1.2 Conversiones y utilidades (coords.py) — nota: `cv_to_three`, `fov_y_deg`, `floor_frame`, `to_column_major` + 10 tests (§4: y<0 abajo-centro, det=+1, x_axis>0, plano sintético, cámara inclinada, d<0 invertido).
- [x] 1.3 Detección del piso — nota: RANSAC del plan + 3 ajustes verificados con las fotos: (1) descartar planos a < 30 cm de la cámara (franjas falsas), (2) usar las normales de MoGe (candidatos y máscara solo en superficies que miran arriba), (3) si hay un plano horizontal ≥ 30 cm más abajo con puntos suficientes (mesón), el piso es el de abajo. 12/13 fotos de cuartos OK; la ducha (08 (5)) → piso_no_encontrado (correcto). `scripts/debug_floor.py` genera los debug.
- [x] 1.4 Malla de oclusión — nota: `occlusion.py` (grilla ≤ 320 px, sin inválidos/saltos > 4 %/piso). En 5 fotos: 97k–144k caras, 1.8–2.6 MB, ~16 ms. Test recarga el GLB con trimesh.
- [x] 1.5 Endpoint POST /api/scenes — nota: `scenes.py` + `storage.py`; guarda image.jpg/scene.json/occlusion.glb/floor_mask.png/depth.png/debug.jpg. Test rápido con MoGe simulado (corre en CI) + test slow con 14 fotos (≥ 80 % con piso y altura 0.8–2.2 m: pasa). curl: ~1.1 s por foto (3.4 s la primera, carga del modelo). HEIC → 400 en español.
- [x] 1.6 Precarga de modelos — nota: `app.prefetch` (MoGe) llamado desde `instalar.command` e `instalar.bat`; mensaje en español si falla la descarga.
- [x] 1.7 Dimensionar el espacio — nota: `room.py`: área (celdas 5 cm), ancho×fondo (minAreaRect; recorte del 2 % sobre celdas, no píxeles), techo (RANSAC mitad superior con normales), confianza; cuadrícula de 1 m + medidas en debug.jpg. Cuarto sintético 4 m × techo 2.4 m: OK. Fotos reales: techo 2.27–2.74 m, sala 3.5×3.8 m visible. Sin `medidas_reales.json` todavía (el test slow lo usa si aparece).
- [x] 🛑 Fin Fase 1 — nota: resultados buenos (piso OK en 12/13 fotos de cuartos, cuadrícula alineada con las baldosas). Por pedido de Gabriela (avanzar sin esperar) se sigue a la Fase 2 y el informe se le entrega en el siguiente mensaje.

## Fase 2
- [x] 2.1 Catálogo: servicio y endpoints — nota: `catalog/service.py` (carpeta por mueble + catalog.json regenerado con escritura atómica y lock), `app.catalog.build`, GET/POST/DELETE /api/catalog (DELETE solo `user_created`). 5 tests.
- [x] 2.2a Importar los muebles de Gabriela — nota: `scripts/import_furniture.py` (idempotente) + `catalog/cutout.py` (rembg birefnet-general-lite, deja solo el objeto principal). Sofás: recortes limpios (se quitan lámpara, planta, libros). Mesa Gretel: el recorte incluye las 4 sillas (no separables) → nota pidiendo foto de la mesa sola. Click-clack: aviso de proporción (foto en 3/4). rembg agregado a `app.prefetch`.
- [x] 2.2b Catálogo complementario Poly Haven — nota: `scripts/seed_catalog.py`, 12 modelos CC0 (sin lámpara de piso ni cama moderna en Poly Haven), GLB 0.2–2.2 MB (webp, sin meshopt porque trimesh no lo lee). Medidas desde el bbox. Orientación de mesa de centro moderna y estantería por revisar en 2.3.
- [x] 2.3 Miniaturas — nota: página interna `/thumb` + `e2e/thumbs.spec.ts` + `scripts/make_thumbs.py` (256×256 transparente). Con vistas frente/lado se corrigió el yaw de la estantería y la mesa de centro moderna (−90°, ancho/fondo intercambiados). Nombres corregidos (sofa_02 es Chesterfield negro, sofa_03 clásico). Dudosas de escala: mesa de pedestal 140×100 cm de alto y sillón mid-century 101×119×117 → preguntar en 🛑 Fase 2.
- [x] 2.4 HDRI de iluminación — nota: `lebombo` 1k (sala con luz natural, bajo contraste, CC0) en `frontend/public/hdri/room_1k.hdr` (1.5 MB). Se usa en 2.6 con `<Environment files>`.
- [x] 2.5 Muebles propios desde foto (recorte 2D) — nota: POST /api/catalog recorta con rembg (`service.apply_cutout`, mismo código que el import), guarda `cutout_ratio` y `photo_warning` (> 15 %); tabla de medidas opcional → medidas.jpg (para 3.6). Página **Catálogo** (/catalogo) con formulario y grilla con medidas y avisos; `billboardSize` en `catalog.ts` (vitest). e2e `catalog.spec.ts` + captura revisada.
- [x] 2.6 Editor 3D: estructura de capas — nota: `Editor3D.tsx` (foto <img> + Canvas transparente con letterbox, cámara con FOV y matrix_world de la escena, oclusión colorWrite=false, grupo del piso con sombras/luces/HDRI), toggles (oclusión, cuadrícula, máscara de piso vía CSS mask, sombras), tarjeta de medidas estimadas. `gridHelper` no dibujaba las líneas hacia el fondo (cruzan detrás de la cámara) → `FloorGrid` propio solo delante de la cámara. Página Estudio con subir foto y escenas previas. `three/math.ts` con tests (mismos casos que coords.py).
- [x] 2.7 Muebles en el editor — nota: `FurnitureModel` (GLB escalado por ancho, yaw_offset, aviso de alto > 15 %), `CutoutBillboard` (mira a la cámara; plano adelantado 40 % del fondo para que la base quede en el borde frontal; sombra de contacto), arrastre por raycast al piso, huella verde/roja + etiqueta de medidas, `fit.ts` (> 10 % fuera de floor_mask o cruce con otro mueble; tapetes no cuentan). Atajos Q/E, Supr, Cmd+D, Cmd+Z (30 pasos). PUT /api/scenes/{id}/placements + autoguardado 1 s. Paneles de catálogo (búsqueda y categorías) y mueble seleccionado. e2e `furniture.spec.ts` con capturas revisadas.
- [x] 2.8 Calibración de escala — nota: panel Escala ("Calibrar medida", 2 clics en el piso + cm reales → scale_k = escena/real, restablecer), marcadores con la distancia en la foto; la cuadrícula y las medidas del espacio se ajustan con scale_k; se guarda con el autoguardado. En la sala, 2 puntos ≈ 1.8 baldosas midieron 109 cm (≈ 108 cm si la baldosa es de 60 cm). Bug encontrado: selector de zustand que crea arreglos nuevos cicla en v5.
- [x] 2.9 Piso manual — nota: panel "Definir piso" si floor.found=false; 3 clics con raycast contra la malla de oclusión → `planeFromPoints` + `floorFrameFromPlane` (math.ts, testeado con los casos de coords.py) → PUT /api/scenes/{id}/floor (nuevo). Con piso manual: sin oclusión (la malla incluye el piso) y sin máscara en ¿cabe?. e2e con la foto de la ducha.
- [x] 2.10 Exportar PNG — nota: `exportImage.ts`: foto + render 3D al tamaño natural (sin ayudas: cuadrícula/huellas/marcadores van en la capa 1, que se apaga al exportar) y máscara de muebles blanco/negro (shader con alfa para recortes, toneMapped=false). Botones "Exportar PNG" y "Máscara de muebles". e2e `photo-studio.spec.ts` (PNG > 50 KB, revisado a ojo: sofá contra la pared, mesa delante con sombra, oclusión correcta).
- [x] 2.11 UI general (PhotoStudio) — nota: layout catálogo (búsqueda + categorías) / editor / panel (mueble, vista, escala, medidas); intensidad de sombra y exposición de muebles (0.5–1.5); avisos (toasts) en español para errores del servidor; al agregar un mueble se busca el lugar libre más cercano (primero dentro del piso visible, si no al menos sin cruces). e2e `studio-ui.spec.ts` + aviso de archivo inválido.
- [x] 🛑 Fin Fase 2 — nota: Gabriela (2026-09-29): tamaños correctos, pero posiciones poco naturales y falta realismo → prioridad en Fase 3 (ubicación) y Fase 4 (luz/sombras). Se quitaron sillón mid-century y mesa de pedestal. Release NO se envía todavía. Sofás verificados.

## Fase 3
- [x] 3.1 Grilla de ocupación — nota: `geometry/occupancy.py` (celdas 10 cm: libre / cerca de obstáculo (< 20 cm) / borde de pared (obstáculo > 1.2 m, con dirección a la pared) / bloqueado (0.05–1.8 m) / desconocido; celdas fuera de la foto = desconocidas). `occupancy.png` y `geometry.npz` (puntos f16) por escena para recalcular. Revisado en cuarto sintético y 3 fotos reales (sala, alcoba, cocina en L): coincide.
- [x] 3.2 Heurística — nota: `placement/heuristic.py` + `geometry2d.py` + POST /api/scenes/{id}/suggest. Contra pared (espalda a 5 cm, frente hacia el cuarto; sofá prefiere mirar a la cámara), mesa de centro 45 cm delante del sofá, sillas alrededor de mesa, decoración en esquinas/al lado del sofá, centro del área libre. Hallazgos: (1) promediar ángulos de pared falla porque MoGe "abre" las paredes laterales (~70° en vez de 90°) → la dirección a la pared sale de las **normales de MoGe** (guardadas en geometry.npz), con recta local de respaldo; (2) exigir 100 % de huella libre era muy estricto → tolerancia 3 % desconocido / 2 % bloqueado. Sala: sofá contra la pared del fondo + mesa delante + planta en la esquina; alcoba: sofá cama contra la pared del fondo.
- [x] 3.3 VLM local opcional — nota: Ollama 0.34.4 (brew, servicio) + `qwen3-vl:4b-instruct` (3.3 GB). `placement/vlm.py`: dibuja el top-8 de candidatos por mueble (contorno + número), pide JSON con `format: json`, valida número/item y cruces; si falla → heurística + nota. GET /api/scenes/vlm/status. Prueba en la sala: 71 s (con carga del modelo), razones en español; eligió la mesa de centro girada 90° (menos natural que la heurística). Tests con respuestas simuladas y Ollama apagado.
- [x] 3.4 UI — nota: panel "Sugerir ubicación" (reacomoda los muebles puestos + agrega elegidos), switch "Usar IA local" deshabilitado con motivo si Ollama no está; fantasmas semitransparentes con huella azul punteada (no se exportan), notas, Aceptar / Aceptar todas / Descartar (un solo paso de deshacer). Guarda los muebles antes de pedir la sugerencia.
- [x] 3.5 Tests — nota: cuarto sintético 4×5.6 m → sofá contra la pared del fondo mirando a la cámara, mesa de centro a 45 ± 5 cm delante y alineada, sin cruces (`test_heuristic.py`); VLM con respuestas simuladas/Ollama apagado (`test_vlm.py`); e2e `suggest.spec.ts` (≥ 1 fantasma, aceptar). Capturas antes/fantasmas/aceptadas revisadas.
- [x] 3.6 Leer tabla de medidas automáticamente — nota: `catalog/extract.py` + POST /api/catalog/extract-dimensions (prompt con las reglas de §5.2, validación pydantic/rangos, sin Ollama → 503 "escríbelas a mano"). Formulario de Catálogo se prellena y muestra la fila original; al guardar queda `vlm_extraida` + verificada. **Aciertos: 9/9** (3 tablas × ancho/fondo/alto, ±1 cm), ~8 s por tabla con el modelo cargado.
- [ ] 🛑 Fin Fase 3 — nota: Gabriela (2026-09-29): "las ubicaciones aún no tienen sentido" → marcó: cosas en medio del paso, distribución de sala rara, se ven pegados/flotando. Cambios: corredor de paso (90 cm) desde la cámara hasta el frente del sofá donde solo van mesa de centro/tapete/comedor; se permite que un mueble quede hasta 40 % fuera de cuadro (antes todo debía verse y se amontonaba al centro); plantas/lámparas solo en esquinas (deslizándose a lo largo de la pared) o pegadas al brazo del sofá; al aceptar todas, lo que no tiene lugar sale de la escena. Nueva entrega en `entregas/fase3/comparacion.jpg`. "Flotando" → Fase 4. Segunda ronda (Gabriela): la planta estorbaba el camino de entrada y el sofá de la alcoba no se veía de su medida → recorrido de entrada de 1.2 m, plantas/lámparas solo pegadas al sofá (esquinas solo si no hay sofá), recortes en ángulo ajustados al ANCHO real (antes al alto: el click-clack quedaba de ~155 cm en vez de 203), IA local escondida para ubicar (decisión 2.A).

## Fase 4
- [x] 4.1 Retoque clásico — nota: `geometry/lighting.py` (al analizar: color/brillo medio del piso y posición de la zona más brillante = ventana, en el mundo del piso) + `three/lighting.ts` (ajuste automático al cargar la escena: luz ambiente con el tono del piso, exposición según el brillo, luz direccional desde la ventana → las sombras caen hacia la cámara); controles de dirección/altura/ambiente/exposición + botón "Ajuste automático de luz"; recortes con el tinte del cuarto, sombra de contacto doble y **proyectan sombra** (silueta con alphaTest); exportación con supermuestreo 2× (tope 4096 px). Segunda ronda: sombras de borde suave (PCSS de drei, size 5: con VSM o PCSS grande la sombra casi desaparecía) y reflejo tenue en el piso (recorte invertido con degradado; modelos 3D invertidos al 60 %), control "Reflejo en el piso" (12 % por defecto).
- [x] 4.2 Proveedor IA — nota: DESCARTADO por Gabriela (2026-09-29, opción A). `Qwen/Qwen-Image-Edit-2511` pide 180 s de GPU (ZeroGPU lo cuenta como 360 s) → rechazado para cuenta gratis. Space oficial `Qwen/Qwen-Image-Edit` (120 s → 240 s) funciona: 55 s por imagen, pero **cambia todo el cuarto** (luz dorada, texto de letreros deformado, borra objetos, redibuja el sofá y mueve levemente la cámara). Mezclar solo alrededor de los muebles falla porque la geometría cambia de forma no rígida (ECC afín: bordes coinciden 9 % → 16 %). Cuota gratis: ~5 min/día = **1 retoque al día**. Evidencia en `entregas/fase4/`. `gradio_client` se quitó.
- [x] 4.3 UI — nota: descartada junto con 4.2 (no hay botón de IA). Se mejora el retoque clásico: sombras suaves y reflejo en el piso.
- [x] 🛑 Fin Fase 4 — nota: pares antes/después en `entregas/fase4/`. Gabriela eligió A: sin IA externa, mejorar el retoque clásico (hecho) y seguir a la Fase 5.

## Fase 5
- [x] 5.1 Video a fotogramas clave — nota: `jobs.py` (hilo + JSON, GET /api/jobs/{id}), `video/keyframes.py` con **OpenCV** (su FFmpeg es LGPL; imageio-ffmpeg podía traer binario GPL), `videos.py` (POST /api/videos, GET /api/videos/{id}, POST /api/videos/{id}/keyframes). Por ventana se toman los 3 más nítidos y se elige el que muestra más piso (MoGe): elegir solo por nitidez daba primeros planos de puertas/closets. Límite 3 min (el plan decía 60 s, pensado para 5.2). Video de Gabriela (150 s): 6 fotogramas en ~70 s, 5 con piso; resumen techo ≈ 2.23 m. Página **Video** con progreso, tira de fotogramas y "Amoblar este fotograma". e2e `video.spec.ts`.
- [x] 🛑 Tras 5.1 — nota: Gabriela (2026-09-29): bastan los fotogramas (opción A) → se omiten 5.2–5.3 y la Fase 6; se pasa a la Fase 7.
- [-] 5.2 Seguimiento de cámara (SfM) — nota: omitido por decisión de Gabriela.
- [-] 5.3 Render del video — nota: omitido por decisión de Gabriela.
- [-] 🛑 Tras 5.3 — omitido.

## Fase 6
- [-] 6.1 Proveedor foto→3D — nota: omitido (Gabriela eligió pasar a la Fase 7; usaría Hugging Face con la misma cuota de ~1 uso/día).
- [-] 6.2 Normalización — nota: omitido (Gabriela eligió pasar a la Fase 7; usaría Hugging Face con la misma cuota de ~1 uso/día).
- [-] 6.3 UI — nota: omitido (Gabriela eligió pasar a la Fase 7; usaría Hugging Face con la misma cuota de ~1 uso/día).
- [-] 🛑 Fin Fase 6 — omitido.

## Fase 7
- [x] 7.1 Release zip — nota: `crear_release.sh` copia solo archivos del repo (git ls-files) + interfaz compilada; por defecto sin muebles de fotos de tiendas (`--con-fotos-de-tienda` los incluye). v0.2.0: 6.1 MB, 10 muebles CC0. Probado descomprimido en el Mac: instalar (~2 min con caché) → health, página, catálogo y análisis de foto OK. `instalar.command` ahora instala uv con el instalador oficial (sin Homebrew). CI: jobs `build-release` (Linux) + `release-smoke` (Windows limpio: instalar.bat instala uv y modelos, iniciar.bat, health, página y análisis de una foto) en workflow_dispatch. Run 36589177526: todo verde (Windows limpio instaló uv + modelos, arrancó y analizó una foto).
- [ ] 7.2 Demo en vivo temporal (opcional) — nota:

## Fase R — Realismo automático y video con muebles (pedido de Gabriela, 2026-09-30)
- [x] R.1 Muebles de foto → 3D local con TripoSR (MIT, en `app/vendor/tsr`, ~20–30 s/mueble en MPS) — nota: `catalog/to3d.py`: alineación del giro (huella de área mínima; bug de signo encontrado con vista cenital), escalado por eje a las medidas reales de la tabla, **textura con la foto real proyectada** (cámara de TripoSR: +x, 1.9, fov 40°; z-buffer 512, solo donde el recorte es opaco, bordes rellenados), colores del resto calibrados contra la foto, normales exportadas y material mate (glTF asume metálico = 1). En el editor: albedo 0.62 para no sumar la luz del estudio. Endpoint `POST /api/catalog/{id}/generate-3d` (trabajo) + botón "Convertir a 3D". Sofás de Gabriela convertidos (Gretel no: su foto trae sillas). Mallas simplificadas a 25k caras (fast-simplification, MIT): ~1 MB por mueble. `transformers` fijado < 5 (renombró capas de ViT).
- [x] R.2 ¿Grano/desenfoque de la foto? — nota: medido: la nitidez del mueble renderizado ya coincide con la foto (0.31 vs 0.30) y las fotos de WhatsApp casi no tienen grano → no se aplica.
- [ ] R.3 Luz del entorno desde la propia foto — nota:
- [ ] R.4 Video: seguimiento de cámara (pycolmap) — nota:
- [ ] R.5 Video: profundidad por fotograma (oclusión) y render MP4 — nota:

## Decisiones tomadas con Gabriela
- 2026-09-28: Mesa Gretel se deja como dice la tabla: frente (width) 80 cm, fondo (depth) 140 cm (opción B).
- 2026-09-28: la app arranca en el Mac de Gabriela con doble clic.
- 2026-09-28: HEIC no se soporta (pillow-heif es GPLv2); solo JPG/PNG (opción A).
- 2026-09-28: Gabriela pide avanzar sin preguntar lo técnico e instalar lo necesario (p. ej. Ollama).
- 2026-09-29: medidas de los sofás confirmadas. Catálogo semilla sin sillón mid-century ni mesa de pedestal (escala irreal). Release v0.1.0 no se envía al hermano todavía.
- 2026-09-29: "tamaño correcto, pero posiciones poco naturales y no se ve realista" → prioridad: ubicación natural (Fase 3) y realismo (Fase 4).
- 2026-09-29: IA local solo para leer tablas de medidas; para ubicar muebles se usa la sugerencia básica (opción A).
- 2026-09-29: nada de plantas/decoración en el recorrido desde la puerta de entrada; recortes 2D en ángulo se escalan al ancho real.
- 2026-09-30: prioridad nueva: realismo automático + video con muebles específicos. Aprobó probar TripoSR (MIT) local; usar el video que ya existe.
- 2026-09-29: video: bastan los fotogramas; se omiten 5.2–5.3 y la Fase 6 → Fase 7.
- 2026-09-29: retoque con IA (Hugging Face) descartado: cambia el cuarto y los muebles, y la cuota gratis da 1 imagen al día. Se sigue con el retoque clásico (opción A).

## Problemas abiertos

## Mediciones
### Sugerencias (Fase 3)
| Foto | Básica | IA local | Comentario |
|---|---|---|---|
| Sala | 4.9 s | 62.5 s | sofá contra el fondo + mesa delante; IA eligió posiciones parecidas |
| Sala desde la entrada | 5.8 s | 51.1 s | sofá al fondo + mesa delante; planta queda en medio (mejorable) |
| Alcoba | 3.8 s | 38.0 s | solo cabe el sofá cama |
| Tablas de medidas (3.6) | — | ~8 s/tabla | 9/9 aciertos |

| Foto | Dispositivo | Tiempo análisis | Altura cámara | % piso |
|---|---|---|---|---|
| 10.04.07 (1) | mps | 1.5 s (1.ª, incluye calentamiento) | 1.24 m | 36 % |
| 10.04.07 (2) | mps | 0.96 s | 1.59 m | 12 % |
| 10.04.07 (3) cocina | mps | 0.96 s | 1.47 m | 2 % |
| 10.04.07 (4) | mps | 0.94 s | 1.45 m | 5 % |
| 10.04.07 pasillo | mps | 0.94 s | 1.16 m | 19 % |
| 10.04.08 (1) | mps | 0.96 s | 1.45 m | 11 % |
| 10.04.08 (2) | mps | 0.94 s | 1.41 m | 21 % |
| 10.04.08 (3) | mps | 0.96 s | 1.27 m | 6 % |
| 10.04.08 (4) baño | mps | 0.94 s | 1.27 m | 12 % |
| 10.04.08 (5) ducha | mps | 0.94 s | — (no se ve piso) | 0 % |
| 10.04.08 (6) baño | mps | 0.94 s | 1.03 m | 2 % |
| 10.04.08 (7) baño | mps | 0.94 s | 1.38 m | 4 % |
| 10.04.08 (8) vista ventana | mps | 0.94 s | 7.63 m (patio exterior) | 8 % |
| 10.04.08 ventana | mps | 0.96 s | 1.32 m | 1 % |

### Medidas estimadas del espacio (1.7)
| Foto | Altura cámara | Visible ancho×fondo | Área visible | Techo | Confianza |
|---|---|---|---|---|---|
| 10.04.07 (1) sala | 1.24 m | 3.5×3.8 m | 10.7 m² | 2.33 m | alta |
| 10.04.07 (2) cocina | 1.59 m | 2.9×2.8 m | 3.6 m² | 2.70 m | media |
| 10.04.07 pasillo→sala | 1.16 m | 3.0×5.8 m | 10.8 m² | 2.28 m | media |
| 10.04.08 (1) | 1.45 m | 2.1×1.9 m | 2.5 m² | 2.36 m | media |
| 10.04.08 (2) alcoba | 1.41 m | 2.6×1.8 m | 3.9 m² | 2.48 m | alta |
| 10.04.08 (3) | 1.27 m | 1.0×2.8 m | 1.8 m² | 2.27 m | baja |
| resto (baños, ventana) | — | < 1.5 m² visibles | — | — | baja |
