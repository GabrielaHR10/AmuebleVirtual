# PLAN DE DESARROLLO — Estudio Virtual de Amoblado (Santiago Muebles)

> Documento para el agente de código (Claude Code). Léelo completo antes de empezar.
> La dueña del proyecto es **Gabriela**. Cuando este plan diga **🛑 PARAR Y PREGUNTAR**, detente,
> presenta lo hecho y espera su respuesta antes de seguir.

---

## 0. Cómo usar este plan (reglas para el agente)

1. Trabaja **en orden**: Fase 0 → 1 → 2 → … Dentro de cada fase, tarea por tarea (0.1, 0.2, …).
2. Antes de cada tarea, relee su sección. Al terminarla:
   - Corre las verificaciones indicadas en "✅ Verificar".
   - Marca la tarea en `PROGRESO.md` (ver plantilla en §9) con una nota de 1–3 líneas.
   - Haz `git commit` con mensaje `fase X.Y: <resumen corto>`.
3. **No te adelantes** a tareas futuras ni hagas refactors fuera del alcance de la tarea actual.
4. Si el mismo error persiste después de **2 intentos distintos**, para, escribe en `PROGRESO.md`
   qué intentaste y qué pasó, y pregunta a Gabriela (§8).
5. Todo lo que ve el usuario (UI, mensajes, README, guías) va **en español**.
   Código, nombres de variables, claves JSON y commits: identificadores en **inglés**, comentarios en español están bien.
6. Costo objetivo: **$0**. Prohibido agregar servicios pagos o que requieran tarjeta de crédito.
7. Licencias permitidas para código/modelos/assets: **MIT, Apache-2.0, BSD, CC0, CC-BY**.
   Prohibido sin preguntar: cualquier licencia **NC / no comercial** (ej. CC-BY-NC, FLUX.1-dev,
   SegFormer de NVIDIA, DUSt3R/MASt3R, Depth-Anything V2 Base/Large). Registra cada dependencia de
   modelo o asset en `THIRD_PARTY.md` (nombre, URL, licencia).
8. Nunca subas secretos. `HF_TOKEN` y similares van en `.env` (en `.gitignore`); mantén `.env.example`.
9. Archivos de código de máximo ~400 líneas; si crecen, divídelos.
10. Cuando una tarea diga "inspecciona la API", hazlo de verdad (imprime firmas/salidas) antes de
    escribir el adaptador. Las APIs de Hugging Face Spaces cambian.

---

## 1. Objetivo y alcance

**Producto a largo plazo:** plataforma para arrendar muebles del hogar. Dueños de apartamentos
amoblan su inmueble arrendando muebles de terceros para subir el valor del arriendo.

**Lo que construimos AHORA (este plan):** el **Estudio Virtual**:
1. El usuario sube **una foto** (o un **video**) de un espacio, idealmente vacío.
2. Elige muebles de un **catálogo** (muebles reales que se pueden arrendar).
3. El sistema muestra el espacio **amoblado con esos muebles exactos**, con escala real,
   sombras y oclusión, y **sugiere dónde ubicarlos**.
4. Opcionalmente, una pasada de **IA** mejora luz/sombras **sin cambiar el mueble**.
5. Se exporta la imagen (PNG) o el video (MP4).

**Principios de producto:**
1. El mueble que se ve debe ser el mueble que se arrienda ("mueble exacto + retoque IA opcional").
2. **Proporciones reales.** Cada mueble del catálogo tiene sus **medidas reales en cm** guardadas en JSON.
   El usuario **no** da medidas del espacio: el sistema **las estima** desde la foto o el video (piso, ancho y fondo
   visibles, altura de techo) y con eso muestra cada mueble **a escala**. También avisa si un mueble no cabe.

**Fuera de alcance ahora:** usuarios/login, pagos, marketplace de arriendo, deploy en la nube,
app móvil, AR en vivo. Todo corre **localmente** (`http://localhost:8000`).

---

## 2. Decisiones técnicas (no cambiar sin 🛑 preguntar)

| Parte | Elección | Por qué |
|---|---|---|
| Frontend | **Vite + React + TypeScript (strict)** + **three.js** vía **@react-three/fiber** y **@react-three/drei**, estado con **zustand**, estilos con **Tailwind CSS** | Gratis, corre en el navegador, fácil de compartir. No Unity: Unity sirve para apps nativas/AR y sus builds web son pesados. |
| Backend | **Python 3.12** + **FastAPI** + **uvicorn**, gestionado con **uv** | uv instala Python solo; funciona igual en Mac y Windows. |
| Geometría de la foto | **MoGe-2** (Microsoft, MIT), modelo `Ruicheng/moge-2-vitb-normal` (104M params) | Una sola red da: nube de puntos **métrica** (metros), profundidad, normales, máscara e **intrínsecos/FOV** de la cámara. Corre en CPU/MPS. Alternativa rápida: `Ruicheng/moge-2-vits-normal` (35M). |
| Quitar fondo a fotos de muebles | **rembg** (MIT) con modelo `birefnet-general-lite` (MIT); fallback `isnet-general-use` | Local y gratis. |
| Catálogo inicial 3D | Modelos **CC0 de Poly Haven** (API `https://api.polyhaven.com`, requiere header `User-Agent: SantiagoMuebles/0.1`) | Gratis, uso comercial permitido, escala real en metros. Dar crédito a Poly Haven en la UI. |
| Ubicación inteligente | **Heurística geométrica** (siempre) + **VLM local opcional**: `qwen3-vl:4b-instruct` vía **Ollama** | Gratis, sin API key, cabe en 16 GB de RAM. |
| Retoque IA (opcional) | Hugging Face Space de **Qwen-Image-Edit-2511** (Apache-2.0) vía `gradio_client` con `HF_TOKEN` gratis | Cuota gratis ZeroGPU ≈ 5 min GPU/día. Siempre hay modo "clásico" local sin IA. |
| Foto de mueble → 3D (opcional) | HF Space **microsoft/TRELLIS.2** (MIT); fallback Space de **TripoSR** (MIT) | Gratis con cuota. Fallback permanente: "modo recorte 2D". |
| Video: seguimiento de cámara | **pycolmap** (BSD, wheels para Mac ARM y Windows) | SfM clásico, sin licencias NC. |
| Codificar video | **imageio-ffmpeg** (trae ffmpeg incluido) | Nadie tiene que instalar ffmpeg. |
| Tests | **pytest** (backend), **vitest** (utilidades TS), **Playwright** (e2e con capturas) | El agente puede ver capturas para verificar visualmente. |

**Dispositivo de cómputo:** variable de entorno `DEVICE` (`auto` | `cpu` | `mps` | `cuda`). En `auto`:
`cuda` si existe, si no `mps` (Mac), si no `cpu`. Si un modelo falla en `mps`, reintentar en `cpu` y
registrar un aviso en el log.

---

## 3. Arquitectura y estructura del repositorio

```
santiago-muebles/
├── CLAUDE.md                 # reglas cortas para el agente (ya existe)
├── PLAN.md                   # este archivo
├── PROGRESO.md               # checklist vivo (lo crea el agente en 0.1)
├── THIRD_PARTY.md            # modelos/assets/licencias
├── README.md                 # cómo instalar y correr (español, para humanos)
├── .env.example              # HF_TOKEN=, DEVICE=auto, OLLAMA_URL=http://localhost:11434
├── .gitignore                # .env, node_modules, .venv, data/scenes, data/videos, release/, backend/app/static/
├── backend/
│   ├── pyproject.toml        # proyecto uv
│   ├── app/
│   │   ├── main.py           # FastAPI: monta /api y sirve frontend compilado desde app/static
│   │   ├── run.py            # arranca uvicorn en 127.0.0.1:8000 y abre el navegador
│   │   ├── config.py         # rutas, DEVICE, lectura de .env
│   │   ├── schemas.py        # modelos pydantic (Scene, CatalogItem, Placement, Job…)
│   │   ├── storage.py        # guardar/leer archivos en data/
│   │   ├── jobs.py           # trabajos en segundo plano (hilo + estado en JSON)
│   │   ├── geometry/
│   │   │   ├── moge_runner.py    # carga perezosa del modelo y inferencia
│   │   │   ├── coords.py         # conversiones OpenCV↔three, fov, matrices
│   │   │   ├── floor.py          # RANSAC del piso, marco del piso
│   │   │   ├── occlusion.py      # malla de oclusión GLB
│   │   │   ├── room.py           # medidas estimadas del espacio (1.7)
│   │   │   └── occupancy.py      # grilla de ocupación (Fase 3)
│   │   ├── catalog/
│   │   │   ├── service.py        # CRUD del catálogo (JSON)
│   │   │   ├── cutout.py         # rembg
│   │   │   └── polyhaven.py      # descarga del catálogo semilla
│   │   ├── placement/            # Fase 3: heuristic.py, vlm.py
│   │   ├── providers/            # Fase 4/6: hf_edit.py, hf_3d.py
│   │   ├── video/                # Fase 5: keyframes.py, sfm.py, encode.py
│   │   └── static/               # build del frontend (generado, en .gitignore salvo en el release)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api/client.ts
│   │   ├── store/useStudio.ts
│   │   ├── three/            # Editor3D.tsx, FurnitureModel.tsx, CutoutBillboard.tsx,
│   │   │                      # OcclusionMesh.tsx, ShadowFloor.tsx, math.ts, exportImage.ts
│   │   ├── components/       # UploadPanel, CatalogPanel, Toolbar, SuggestPanel, RetouchPanel…
│   │   └── pages/            # PhotoStudio.tsx, VideoStudio.tsx, CatalogAdmin.tsx
│   ├── public/hdri/room_1k.hdr   # HDRI interior CC0 de Poly Haven (descargar en 2.4)
│   └── e2e/                  # tests Playwright
├── data/
│   ├── catalog/              # catalog.json + carpetas por mueble (sí se versiona el semilla)
│   ├── scenes/               # escenas subidas (NO versionar)
│   └── videos/               # (NO versionar)
├── samples/                  # fotos/videos de prueba que entrega Gabriela
│   ├── rooms/      (fotos del apartamento + medidas_reales.json opcional)
│   ├── videos/
│   └── furniture/<mueble>/  (foto.jpg + medidas.png → el agente crea mueble.json)
└── scripts/
    ├── mac/instalar.command   mac/iniciar.command
    ├── windows/instalar.bat   windows/iniciar.bat
    ├── build_frontend.sh      # npm ci && npm run build → backend/app/static
    └── crear_release.sh       # arma el .zip para el hermano (Fase 7)
```

**Flujo de datos (foto):**
Navegador sube foto → `POST /api/scenes` → backend corre MoGe-2 → calcula piso, marco, malla de
oclusión → responde `scene.json` → el editor 3D pone la foto de fondo, una cámara three.js con el
mismo FOV, el "marco del piso" y los muebles → el usuario arrastra/rota → exporta PNG.

---

## 4. Convenciones de coordenadas (CRÍTICO — léelo dos veces)

- **MoGe / OpenCV (cámara):** x → derecha, **y → abajo**, **z → adelante**. Unidades: metros.
- **three.js (cámara):** x → derecha, **y → arriba**, **z → hacia atrás** (la cámara mira a −z).
- **Conversión OpenCV → three:** `(x, y, z) → (x, −y, −z)`. Aplica igual a puntos y normales.
  Hazlo **una sola vez en el backend** (`coords.py::cv_to_three`). Todo lo que sale por la API está en coordenadas three.
- **Escena de foto:** la cámara three.js está en el origen, sin rotación (`matrixWorld = identidad`).
- **Intrínsecos de MoGe:** se espera que vengan **normalizados** (fx/W, fy/H, cx/W, cy/H).
  VERIFICA en la tarea 1.1 imprimiéndolos: si `cx ≈ 0.5` están normalizados. Documenta el hallazgo en `coords.py`.
- **FOV vertical:** `fov_y_deg = degrees(2 · atan(0.5 / fy_norm))` (equivale a `2·atan(H / (2·fy_px))`).
  Asumimos punto principal centrado (ignorar cx, cy en v1).
- **Plano del piso:** `n · p + d = 0`, con `n` unitario **apuntando hacia arriba (hacia el lado de la cámara)**.
  Como la cámara está en el origen: `d = distancia cámara–piso = altura de cámara > 0`.
  Si al ajustar sale `d < 0`, invierte el signo de `n` y `d`.
- **Marco del piso (`floor_frame`)**: matriz 4×4 que convierte de "mundo del piso" a "cámara three".
  En el mundo del piso: **el piso es y = 0, arriba es +y**, y el eje +z apunta (horizontalmente) hacia la cámara.
  ```
  y_axis = n
  f      = (0,0,-1) − ((0,0,-1)·n) n ; normalizar      # adelante de la cámara, proyectado al piso
  z_axis = −f
  x_axis = y_axis × z_axis                             # producto cruz; debe dar ≈ derecha
  origin = −d · n                                      # pie de la cámara sobre el piso
  floor_frame = columnas [x_axis, y_axis, z_axis, origin]  (4x4, última fila 0,0,0,1)
  ```
  Se envía como 16 números **column-major** (para `THREE.Matrix4().fromArray(...)`).
- **Regla de oro del frontend:** todo mueble, sombra y plano de arrastre va **dentro de**
  `<group matrixAutoUpdate={false} matrix={floorFrame}>`. Ahí dentro se trabaja como en un mundo normal:
  piso y=0, arriba +y, metros. La malla de oclusión va **fuera** de ese grupo (está en coords de cámara).
- **Escala:** por defecto 1 unidad = 1 metro. `scene.scale_k` (default 1.0) multiplica el tamaño de los muebles
  tras la calibración manual (Fase 2.8).
- **Muebles GLB:** convención glTF: +y arriba, el frente mira a **+z** (hacia la cámara por defecto).
  Si un modelo mira a otro lado, se corrige con `yaw_offset_deg` en su ficha del catálogo.

**Tests obligatorios de convenciones** (tarea 1.2): un píxel en la parte inferior central de una foto normal
debe tener `y < 0` (three); `det(floor_frame[:3,:3]) ≈ +1`; `x_axis` debe tener componente x > 0.

---

## 5. Contratos de datos y API

### 5.1 `Scene` (respuesta de `POST /api/scenes` y `GET /api/scenes/{id}`)
```json
{
  "id": "scn_20260928_153012_ab12",
  "kind": "photo",
  "image": { "url": "/files/scenes/scn_.../image.jpg", "width": 1920, "height": 1440 },
  "camera": { "fov_y_deg": 58.3, "intrinsics_norm": [[0.78,0,0.5],[0,1.04,0.5],[0,0,1]],
              "matrix_world": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] },
  "floor": {
    "found": true,
    "normal": [0.01, 0.97, 0.24],
    "d": 1.41,
    "inlier_ratio": 0.33,
    "frame": [16 números column-major]
  },
  "camera_height_m": 1.41,
  "scale_k": 1.0,
  "room_estimate": {
    "visible_floor_area_m2": 11.8,
    "floor_extent_m": { "width": 3.9, "depth": 4.6 },
    "ceiling_height_m": 2.42,
    "confidence": "media",
    "method": "moge2_metric"
  },
  "warnings": ["escala_dudosa"],
  "assets": {
    "occlusion_glb": "/files/scenes/scn_.../occlusion.glb",
    "floor_mask_png": "/files/scenes/scn_.../floor_mask.png",
    "depth_preview_png": "/files/scenes/scn_.../depth.png",
    "debug_jpg": "/files/scenes/scn_.../debug.jpg"
  },
  "placements": [],
  "model": "Ruicheng/moge-2-vitb-normal",
  "timings_ms": { "load": 0, "infer": 0, "floor": 0, "mesh": 0 }
}
```
Warnings posibles: `piso_no_encontrado`, `escala_dudosa` (altura de cámara fuera de 0.8–2.2 m),
`poco_piso_visible` (inlier_ratio < 0.08).

### 5.2 `CatalogItem` (en `data/catalog/catalog.json`, lista)
El catálogo es **la fuente de verdad de las medidas**. `catalog.json` se regenera a partir de las carpetas de
`data/catalog/<id>/mueble.json` (una carpeta por mueble) con `uv run python -m app.catalog.build`.
```json
{
  "id": "sofa-gris-3p",
  "name": "Sofá gris tres puestos",
  "category": "sofa",
  "dimensions_cm": { "width": 210, "depth": 90, "height": 85 },
  "extra_dimensions_cm": { "seat_height": 45, "arm_height": 62 },
  "dimensions_source": "tabla_medidas",
  "dimensions_verified": true,
  "monthly_price_cop": null,
  "preferred_mode": "cutout",
  "glb_url": null,
  "cutout_url": "/files/catalog/sofa-gris-3p/cutout.png",
  "photo_url": "/files/catalog/sofa-gris-3p/foto.jpg",
  "thumb_url": "/files/catalog/sofa-gris-3p/thumb.png",
  "yaw_offset_deg": 0,
  "against_wall": true,
  "source": "Fotos de prueba de Gabriela",
  "license": "solo pruebas internas"
}
```
**Definición de medidas (obligatoria, igual en todo el código):**
- `width` = **ancho de frente**: el lado que se ve cuando miras el mueble de frente (en la tabla suele decir *Ancho*, *Largo*, *Frente*).
- `depth` = **fondo**: de adelante hacia atrás (*Fondo*, *Profundidad*). En **camas**, `depth` es el *largo* (de cabecera a pies) y `width` el *ancho*.
- `height` = **alto total** (*Alto*, *Altura*). Otras medidas (alto del asiento, del brazo, diámetro…) van en `extra_dimensions_cm`.
  Mesas redondas: `width = depth = diámetro`.
- Unidades: todo se guarda en **cm**. Convertir si la tabla viene en m, mm o pulgadas (1 in = 2.54 cm).
- Si una tabla es ambigua (p. ej. dice "Largo" y "Ancho" en un sofá y no es claro cuál es el frente), **🛑 pregunta**.

`dimensions_source` ∈ `tabla_medidas | usuario | modelo_3d | vlm_extraida`. `dimensions_verified` = Gabriela las confirmó.
`category` ∈ `sofa, armchair, chair, bed, nightstand, dining_table, coffee_table, desk, tv_stand,
shelf, wardrobe, rug, lamp, plant, other`. `against_wall` por defecto true para sofa, bed, tv_stand,
shelf, wardrobe, desk, nightstand.

### 5.3 `Placement`
```json
{ "uid": "p_1", "item_id": "sofa_02", "mode": "3d", "x": 0.4, "z": -3.1, "yaw_deg": 0,
  "source": "manual" }
```
`x, z` en metros en el mundo del piso; `source` ∈ `manual | heuristic | vlm`.

### 5.4 Endpoints (prefijo `/api`)
| Método | Ruta | Fase | Descripción |
|---|---|---|---|
| GET | `/health` | 0 | `{ok, device, version}` |
| POST | `/scenes` | 1 | multipart `file` (jpg/png/heic→jpg). Crea escena y la analiza (síncrono). |
| GET | `/scenes` / `/scenes/{id}` | 1 | listar / obtener |
| PUT | `/scenes/{id}/placements` | 2 | guarda la lista de placements y `scale_k` |
| GET | `/catalog` | 2 | lista de muebles |
| POST | `/catalog` | 2 | multipart: `photo`, `name`, `category`, `width_cm`, `depth_cm`, `height_cm` → crea con recorte |
| DELETE | `/catalog/{id}` | 2 | borra (solo muebles creados por usuario) |
| POST | `/scenes/{id}/suggest` | 3 | body `{item_ids:[], use_vlm:false}` → `{placements:[], notes:[]}` |
| POST | `/scenes/{id}/retouch` | 4 | multipart `composite`, `mask`, `mode=ai`, `keep_furniture=true` → PNG |
| POST | `/videos` | 5 | multipart `file` → `{video_id, job_id}` |
| GET | `/jobs/{id}` | 5 | `{status: queued|running|done|error, progress 0–1, message, result}` |
| POST | `/videos/{id}/keyframes` | 5 | crea N escenas desde fotogramas |
| POST | `/videos/{id}/track` | 5 | inicia SfM (job) |
| POST | `/videos/{id}/render` | 5 | recibe PNGs de frames renderizados, codifica MP4 (job) |
| POST | `/catalog/extract-dimensions` | 3 | multipart `table_image` → medidas sugeridas (VLM local) |
| POST | `/catalog/{id}/generate-3d` | 6 | job imagen→3D |

Archivos estáticos de datos se sirven en `/files/...` (montar `data/` con `StaticFiles`).
El frontend compilado se sirve en `/` (SPA: rutas desconocidas → `index.html`).

---

## 6. Fases y tareas

### FASE 0 — Esqueleto que corre en Mac y en Windows

**0.1 Repo y documentos base.**
- Crear estructura de §3 (carpetas vacías con `.gitkeep` donde aplique), `.gitignore`, `.env.example`,
  `PROGRESO.md` (plantilla §9), `THIRD_PARTY.md`, `README.md` mínimo.
- ✅ Verificar: `git status` limpio tras commit.

**0.2 Backend mínimo.**
- `cd backend && uv init --app --python 3.12` y agregar: `fastapi`, `uvicorn[standard]`, `python-multipart`,
  `pydantic`, `pillow`, `numpy`, `python-dotenv`. Dev: `pytest`, `httpx`, `ruff`.
- `app/main.py` con `GET /api/health` y montaje de `/files` y del frontend (`app/static`, si existe).
- `app/run.py`: `uvicorn.run(app, host="127.0.0.1", port=8000)` y abre `http://localhost:8000` con
  `webbrowser` 1.5 s después (hilo). Si el puerto está ocupado, mensaje claro en español.
- Test `tests/test_health.py`.
- ✅ Verificar: `cd backend && uv run pytest -q` pasa; `uv run python -m app.run` responde en `/api/health`.

**0.3 Frontend mínimo.**
- `npm create vite@latest frontend -- --template react-ts`; instalar `three @react-three/fiber @react-three/drei zustand`,
  Tailwind (v4 con plugin de Vite), `vitest`, `@playwright/test`.
- Proxy de Vite: `/api` y `/files` → `http://127.0.0.1:8000` (modo desarrollo).
- Página con título "Estudio Virtual — Santiago Muebles", un indicador del `/api/health` y un `<Canvas>` con un cubo.
- `scripts/build_frontend.sh`: `cd frontend && npm ci && npm run build` y copia `dist/` a `backend/app/static/`.
- ✅ Verificar: `npm run build` sin errores de TS; tras `build_frontend.sh`, `http://localhost:8000` muestra la página servida por FastAPI.

**0.4 Scripts de instalación/arranque.**
- `scripts/mac/instalar.command` y `iniciar.command` (ejecutables, `chmod +x`):
  instalar = verifica `uv` (si no, instrucción `brew install uv`), `uv sync` en backend, precarga modelos (Fase 1+).
  iniciar = `cd` a la raíz del repo relativo al script y `uv run --project backend python -m app.run`.
- `scripts/windows/instalar.bat` y `iniciar.bat`:
  si `where uv` falla → `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` y
  agregar `%USERPROFILE%\.local\bin` al PATH de la sesión; luego lo mismo que en Mac.
  Mensajes en español, `pause` al final si hay error.
- **Dependencias git:** el usuario de Windows puede no tener Git. MoGe depende de `utils3d` y `pipeline`
  vía `git+https`. En `backend/pyproject.toml` usar **URLs de archivo zip** de GitHub fijadas a commit
  (`https://github.com/<org>/<repo>/archive/<sha>.zip`) para `moge` y, con
  `[tool.uv] override-dependencies`, para `utils3d` y `pipeline`. (Esto se aplica en Fase 1, pero deja el comentario desde ya.)
- ✅ Verificar: en el Mac, doble clic (o `bash scripts/mac/iniciar.command`) abre el navegador con la app.

**0.5 CI de humo en Windows (GitHub Actions).**
- `.github/workflows/smoke.yml`: jobs en `windows-latest` y `macos-14`: instalar uv (`astral-sh/setup-uv`),
  `uv sync`, `uv run pytest -q -m "not slow"`, arrancar el servidor en background y hacer `GET /api/health`.
- Solo en `workflow_dispatch` y `push` a `main` (para ahorrar minutos).
- ✅ Verificar: `gh workflow run smoke.yml` y `gh run watch` → verde. Si Gabriela no ha conectado `gh`, anótalo en PROGRESO y sigue.

**0.6 Catálogo de medidas desde las carpetas de Gabriela (sin modelos de IA todavía).**
Gabriela entrega una carpeta por mueble:
```
samples/furniture/<nombre-del-mueble>/
    foto.jpg            (1 o más fotos del mueble: foto.jpg, foto_2.jpg…)
    medidas.png         (captura de la tabla de medidas de la tienda; puede ser .jpg)
```
Pasos:
1. Para cada carpeta, **abre y mira tú mismo** (herramienta Read) `medidas.*` y las fotos. Transcribe la tabla a
   `samples/furniture/<carpeta>/mueble.json` con el esquema de §5.2 (campos que no apliquen en `null`), siguiendo la
   **definición de medidas** de §5.2. `id` = nombre de la carpeta en minúsculas con guiones. `dimensions_source: "tabla_medidas"`,
   `dimensions_verified: false`. Guarda también `"raw_table": {"<etiqueta tal cual>": "<valor tal cual>"}` con lo que dice la tabla,
   para poder auditar. Elige la categoría de la lista de §5.2.
2. Si hay varias fotos, marca como `main_photo` la más frontal (de frente, a la altura del centro del mueble).
3. **Chequeo de proporción:** mide en la foto principal la relación ancho/alto aparente del mueble (bounding box aproximado)
   y compárala con `width/height` de la tabla. Si difieren > 25 %, anótalo en `notes` (puede ser foto en ángulo o medidas mal transcritas).
4. Genera `samples/furniture/RESUMEN_MEDIDAS.md`: tabla con carpeta, nombre, categoría, ancho×fondo×alto (cm), extras, notas.
5. Validación con pydantic (`backend/app/schemas.py::FurnitureSpec`): medidas > 0, alto < 300 cm, ancho < 500 cm; test que valida
   todos los `mueble.json`.
- Nota: las fotos de tiendas son **solo para pruebas internas**; el repo debe seguir **privado** y no se publican.
- (En la Fase 2.5 este mismo formato se usa para importar al catálogo; para muebles nuevos subidos desde la UI, la Fase 3.6
  intenta leer la tabla automáticamente con la IA local.)

🛑 **PARAR Y PREGUNTAR (fin Fase 0):** muestra a Gabriela cómo arrancar (`iniciar.command`), una captura de la página,
el estado de la CI y el `RESUMEN_MEDIDAS.md`. Pregunta: "¿Te abrió la app en tu Mac? ¿Las medidas transcritas están bien
(revisa en especial ancho vs. fondo)?" Cuando confirme, pon `dimensions_verified: true` en los que apruebe.
No sigas a Fase 1 sin fotos de prueba en `samples/rooms/` (mínimo 3).

---

### FASE 1 — Entender la foto (geometría con MoGe-2)

**1.1 Ejecutar MoGe-2.**
- Agregar dependencias: `torch`, `torchvision`, `moge` (URL zip fijada, ver 0.4), `trimesh`, `opencv-python-headless`, `scipy`.
- `geometry/moge_runner.py`:
  - Carga perezosa y única (singleton) de `MoGeModel.from_pretrained(MODEL_ID)` en el dispositivo de §2.
    `MODEL_ID` configurable (`MOGE_MODEL` en `.env`, default `Ruicheng/moge-2-vitb-normal`).
  - Redimensiona la imagen para inferencia a **máx. 1024 px** en el lado largo (conserva la original para mostrar).
  - Corre `model.infer(tensor)` y devuelve `points (H,W,3)`, `depth`, `normal`, `mask`, `intrinsics` como numpy.
  - Corrige orientación EXIF antes de todo (`ImageOps.exif_transpose`). Convierte HEIC si llega (agregar `pillow-heif`).
- Script `backend/scripts/probe_moge.py <imagen>` que imprime shapes, rangos, intrínsecos y guarda un PNG de profundidad.
- ✅ Verificar: correr sobre `samples/rooms/*`; anotar en PROGRESO: tiempo por imagen, dispositivo usado y si los intrínsecos vienen normalizados.

**1.2 Conversiones y utilidades (`coords.py`).**
- `cv_to_three(arr)`, `fov_y_deg(intrinsics_norm)`, `floor_frame(n, d) -> 4x4`, `to_column_major(m)`.
- Tests unitarios de §4 (convenciones) + test de `floor_frame` con un plano sintético (`n=(0,1,0), d=1.5` → origin `(0,-1.5,0)`, `x_axis=(1,0,0)`).
- ✅ Verificar: `uv run pytest -q tests/test_coords.py`.

**1.3 Detección del piso (`floor.py`).**
Algoritmo (sobre puntos en coords three, submuestreados a ≤ 20 000 puntos válidos):
1. Candidatos: píxeles con `mask` válido y en la **mitad inferior** de la imagen (fila > 0.45·H).
2. **RANSAC de plano**: 800 iteraciones, umbral de inlier **0.03 m**, semilla fija (reproducible).
   En cada iteración, descartar planos cuya normal forme > **35°** con el "arriba" aproximado de la cámara `(0,1,0)`.
3. Refinar con mínimos cuadrados (SVD) sobre los inliers. Asegurar `d > 0` (ver §4).
4. Máscara del piso: evaluar **todos** los píxeles válidos: `|n·p + d| < 0.04` → piso. Limpiar con
   apertura/cierre morfológico (kernel 5) y quedarse con el componente conectado más grande que toque la mitad inferior.
5. `inlier_ratio` = píxeles de piso / píxeles totales. Warnings según §5.1.
- Si no se encuentra plano con ≥ 5 % de inliers → `floor.found=false` y warning `piso_no_encontrado`
  (el frontend permitirá definir el piso a mano, ver 2.9).
- Tests: plano sintético con ruido gaussiano 1 cm + 30 % outliers → normal con error < 3°, `d` con error < 3 cm.
- ✅ Verificar: tests + imagen `debug.jpg` por cada foto de `samples/rooms/` con el piso pintado en verde semitransparente y la altura de cámara escrita.

**1.4 Malla de oclusión (`occlusion.py`).**
- Submuestrear el mapa de puntos a ≤ 320 px de lado largo. Construir triángulos por grilla (2 por celda).
- Eliminar triángulos: con vértices inválidos (`mask`), con **salto de profundidad** relativo > 4 % entre vértices,
  o cuyos 3 vértices sean **piso** (el piso no debe tapar muebles; de eso se encarga la sombra).
- Exportar GLB con `trimesh` (coords three). Tamaño objetivo < 3 MB.
- ✅ Verificar: el GLB abre en https://gltf-viewer.donmccurdy.com (dile a Gabriela que puede arrastrarlo ahí) o en un test que lo recargue con trimesh y cuente caras > 0.

**1.5 Endpoint `POST /api/scenes`.**
- Guarda en `data/scenes/<id>/`: `image.jpg` (original corregida, máx. 2560 px lado largo, calidad 90),
  `scene.json`, `occlusion.glb`, `floor_mask.png` (tamaño de la imagen guardada), `depth.png`, `debug.jpg`.
- Respuesta = `Scene` (§5.1). Tiempos en `timings_ms`.
- Test `slow` (marcado `@pytest.mark.slow`) que procesa `samples/rooms/` (si existen) y verifica: `floor.found`, `0.8 < camera_height_m < 2.2`.
- ✅ Verificar: `uv run pytest -q -m slow` y una llamada con `curl -F file=@samples/rooms/<foto> localhost:8000/api/scenes`.

**1.6 Precarga de modelos.** `instalar.*` debe correr `uv run python -m app.prefetch` que descarga los pesos de MoGe (y más adelante rembg) para que el primer uso no tarde.

**1.7 Dimensionar el espacio (`geometry/room.py`) — el usuario NO da medidas, se estiman.**
- Llevar los puntos del piso al mundo del piso (inversa de `floor_frame`); quedarse con x, z.
- `visible_floor_area_m2`: rasterizar en celdas de 5 cm y contar celdas con piso × 0.0025.
- `floor_extent_m`: rectángulo de área mínima (`cv2.minAreaRect`) sobre los puntos del piso, descartando el 2 % de puntos
  más extremos (outliers). `width` = lado más paralelo al eje x del mundo del piso, `depth` = el otro.
  Aclarar en la UI que es **lo visible** en la foto, no necesariamente todo el cuarto.
- `ceiling_height_m`: RANSAC de plano sobre puntos de la **mitad superior** con normal casi opuesta a la del piso (±20°)
  a más de 1.8 m del piso; altura = distancia entre planos. Si no se ve techo → `null`.
- `confidence`: `alta` si `inlier_ratio ≥ 0.2` y altura de cámara entre 1.0 y 1.8 m; `baja` si hay warnings; si no `media`.
- Se guarda en `scene.room_estimate` (§5.1). Si el usuario calibra la escala (2.8), recalcular dividiendo por `scale_k`.
- En `debug.jpg`: dibujar una **cuadrícula de 1 m** sobre el piso (proyectada con la cámara) y escribir las medidas estimadas.
- **Validación con medidas reales:** si existe `samples/rooms/medidas_reales.json`
  (`{"<archivo>": {"ancho_m": 3.5, "fondo_m": 4.2, "techo_m": 2.4, "nota": "sala"}}`), el test `slow` calcula el error % por
  medida y lo escribe en `PROGRESO.md` (tabla de Mediciones). Objetivo orientativo: error ≤ 15 %.

🛑 **PARAR Y PREGUNTAR (fin Fase 1):** entrega a Gabriela una tabla (foto → altura de cámara, % de piso, ancho×fondo visible,
techo, error vs. medidas reales si las dio, tiempo) y las imágenes `debug.jpg` con la cuadrícula de 1 m.
Pregunta: "¿El verde cubre bien el piso? ¿Los cuadros de la cuadrícula parecen de 1 m? ¿Las medidas estimadas se parecen a las reales?"
Si falla en más de la mitad de las fotos, propón: (a) probar `moge-2-vitl-normal`, (b) ajustar umbrales, (c) piso manual. Espera su elección.

---

### FASE 2 — Catálogo y editor 3D sobre la foto (el corazón del MVP)

**2.1 Catálogo: servicio y endpoints.** `catalog/service.py` lee/escribe `data/catalog/catalog.json` con bloqueo simple
(escritura atómica: escribir temporal y renombrar). Endpoints `GET/POST/DELETE /api/catalog`. Validación con pydantic.

**2.2a Importar los muebles de Gabriela (catálogo principal).** Script `backend/scripts/import_furniture.py`:
- Para cada `samples/furniture/<carpeta>/` con `mueble.json` válido: crear `data/catalog/<id>/` con `mueble.json`, `foto.jpg`
  (la `main_photo`) y el recorte (ver 2.5); luego regenerar `catalog.json` (`app.catalog.build`).
- Muebles con `dimensions_verified: false` se importan pero la UI los marca con "medidas sin verificar".
- Idempotente: correrlo dos veces no duplica nada.

**2.2b Catálogo complementario 3D desde Poly Haven.** Script `backend/scripts/seed_catalog.py`:
- `GET https://api.polyhaven.com/assets?t=models&c=furniture` (header `User-Agent: SantiagoMuebles/0.1`).
- Elegir ~10 modelos de hogar variados (sofás, sillón, mesa de centro, mesa de comedor, sillas, cama si hay,
  mueble TV/estantería, lámpara, planta). **Lista propuesta → se confirma en el 🛑 del fin de la Fase 2** (puedes descargar primero y ajustar luego).
- Para cada uno: `GET https://api.polyhaven.com/files/{id}` → descargar la variante **gltf 1k** (y sus texturas),
  convertir a **GLB único** con `trimesh` o con `npx @gltf-transform/cli copy in.gltf out.glb`
  (+ `gltf-transform optimize` con texturas webp y simplificación moderada; objetivo < 5 MB por mueble).
- Calcular `dimensions_cm` desde el bounding box (Poly Haven está en metros). Renderizar miniatura (ver 2.3).
- Registrar cada modelo en `THIRD_PARTY.md` y mostrar "Modelos 3D: Poly Haven (CC0)" en la UI.

**2.3 Miniaturas.** Generar `thumb.png` 256×256: para GLB, con una página oculta del frontend + Playwright
(`e2e/thumbs.spec.ts` que carga cada GLB, encuadra y guarda captura) **o** con `trimesh` + `pyrender` si es más simple.
Para muebles de foto, la miniatura es el recorte.

**2.4 HDRI de iluminación.** Descargar un HDRI interior CC0 de Poly Haven a 1k (`.hdr`) en `frontend/public/hdri/room_1k.hdr`.
Usarlo con `<Environment files="/hdri/room_1k.hdr" />` (NO usar `preset=`, que descarga de internet en tiempo de ejecución).

**2.5 Muebles propios desde foto (modo recorte 2D).**
- `catalog/cutout.py` con `rembg` (`new_session("birefnet-general-lite")`, fallback `isnet-general-use`):
  quitar fondo, recortar al bounding box del alfa (+2 % margen), guardar `cutout.png` (máx. 1024 px) y `thumb.png`.
- `POST /api/catalog` crea el mueble con `preferred_mode: "cutout"`. El import de 2.2a usa esta misma función.
- **Proporción del recorte:** `r_foto = ancho_px/alto_px` del recorte vs. `r_tabla = width/height`. Si difieren ≤ 15 %, el
  billboard usa exactamente `width × height` de la tabla. Si difieren más, conservar la proporción de la foto ajustando
  al **alto** de la tabla y mostrar aviso "La foto no está de frente o las medidas no coinciden".
- Página `CatalogAdmin` en el frontend: formulario (foto, **foto de la tabla de medidas opcional**, nombre, categoría,
  ancho/fondo/alto en cm) y grilla del catálogo con las medidas visibles en cada tarjeta ("210 × 90 × 85 cm").
  Texto de ayuda: "Toma la foto de frente, a la altura del centro del mueble, con fondo despejado y buena luz".
- Tests: recorte de `samples/furniture/*` produce PNG con canal alfa y bbox > 0.

**2.6 Editor 3D (`three/Editor3D.tsx`) — estructura de capas.**
- Contenedor con la **foto como `<img>` de fondo** y encima un `<Canvas>` **transparente** (`gl={{ alpha: true, preserveDrawingBuffer: true, antialias: true }}`)
  del mismo tamaño y relación de aspecto exacta de la foto (letterbox con CSS). Así la foto no pasa por el tone mapping.
- Cámara: `PerspectiveCamera` con `fov = scene.camera.fov_y_deg`, `aspect = W/H`, `near 0.05`, `far 100`,
  `matrixWorld` desde `scene.camera.matrix_world` (identidad en fotos, pero soportarlo desde ya: la Fase 5 lo usará).
  **Sin OrbitControls**: la cámara está fija a la foto.
- `OcclusionMesh`: carga `occlusion_glb` con material `MeshBasicMaterial({ colorWrite: false })`, `renderOrder = -1`.
  Toggle "Oclusión" (on por defecto).
- `<group matrixAutoUpdate={false} matrix={floorFrame}>` que contiene:
  - `ShadowFloor`: plano 30×30 m en y = 0.001 con `ShadowMaterial({ opacity: 0.3 })`, `receiveShadow`.
  - Plano invisible de arrastre (y = 0) para raycast.
  - Luces: `hemisphereLight` (intensidad 0.8) + `directionalLight` con `castShadow` en (2, 4, 2),
    `shadow.mapSize 2048`, cámara de sombra ±6 m. `<Environment>` con el HDRI (intensidad 0.6, `background={false}`).
  - Los muebles (`FurnitureModel` o `CutoutBillboard`).
- Debug toggle: mostrar la máscara del piso encima (útil para Gabriela).
- Toggle **"Cuadrícula 1 m"** (on por defecto la primera vez): `gridHelper` de drei/three en y = 0.002 dentro del grupo del piso,
  líneas cada 1 m, semitransparente. Es la forma más rápida de ver si la escala estimada es creíble.
- Tarjeta **"Medidas estimadas del espacio"** (de `room_estimate`): área visible, ancho × fondo visibles, altura de techo, confianza,
  con la nota "Estimadas desde la foto; pueden variar ±15 %. Usa 'Calibrar medida' si conoces una medida real".

**2.7 Muebles en el editor.**
- `FurnitureModel` (GLB): cargar con `useGLTF`; clonar (`SkeletonUtils.clone` o `scene.clone(true)`); calcular bbox;
  centrar en x/z, apoyar min y en 0; escala **uniforme** = `(width_cm/100 · scale_k) / bbox.width`; si la altura resultante
  difiere > 15 % de `height_cm`, mostrar aviso en el panel. Aplicar `yaw_offset_deg`. `castShadow` en todos los meshes.
- `CutoutBillboard` (2D): plano con textura del recorte (`alphaTest 0.5`, `transparent`), ancho = width, alto = height,
  apoyado en y = 0, rota solo en yaw para mirar siempre a la cámara (en `useFrame`). Sombra de contacto: plano con textura
  de degradado radial (generada en canvas) de tamaño width × depth en y = 0.002, opacidad 0.45.
- Interacción:
  - Clic en mueble del catálogo → se agrega en el centro del piso visible (punto del piso bajo el centro de la imagen;
    si no hay, a 3 m frente a la cámara).
  - Arrastrar con el mouse: raycast al plano y=0 → mover `x, z`. Seleccionado = contorno/`Outlines` de drei o bbox helper.
  - Rotar: slider 0–360° y teclas `Q/E` (±15°). Borrar: `Supr/Backspace`. Duplicar: `Ctrl/Cmd+D`.
  - Deshacer/rehacer simple (historial de placements, 30 pasos) con `Ctrl/Cmd+Z`.
- Estado en zustand; `PUT /api/scenes/{id}/placements` con debounce de 1 s (autoguardado).
- **¿Cabe?** Al mover un mueble, proyectar su huella (width × depth rotada) sobre `floor_mask`: si > 10 % cae fuera del piso
  visible o se cruza con otro mueble, contorno **rojo** y texto "No cabe aquí / se cruza con <mueble>". Verde si está bien.
- Etiqueta opcional sobre el mueble seleccionado con sus medidas reales ("210 × 90 × 85 cm").

**2.8 Calibración de escala (opcional para el usuario).** Botón "Calibrar medida": el usuario hace clic en 2 puntos del piso
y escribe la distancia real (cm) → `scale_k = distancia_en_escena / distancia_real`. Mostrar la escala actual.

**2.9 Piso manual (si `floor.found=false`).** Modo "Definir piso": el usuario hace clic en 3 puntos del piso en la foto;
usando la malla de oclusión (o la profundidad) se obtienen los 3 puntos 3D y el plano; recalcular `floor_frame` en el frontend
con la misma fórmula de §4 (implementar en `three/math.ts` y testear con vitest contra los mismos casos que `coords.py`).

**2.10 Exportar PNG (`three/exportImage.ts`).**
- Canvas 2D del tamaño natural de la foto: dibujar la foto, luego renderizar three a ese tamaño (`gl.setSize(W,H,false)`,
  ajustar `camera.aspect`, `gl.render`, `drawImage(gl.domElement)`) y restaurar tamaño. Descargar `amoblado_<fecha>.png`.
- También poder generar la **máscara de muebles** (blanco sobre negro, mismos tamaños) — la usa la Fase 4.
- Test e2e Playwright `photo-studio.spec.ts`: subir `samples/rooms/<primera>`, esperar análisis, agregar 2 muebles,
  mover uno, exportar → archivo existe y pesa > 50 KB. Guardar captura en `frontend/test-results/`.
  **Abre y mira la captura** para verificar que el mueble está apoyado en el piso y con tamaño creíble.

**2.11 UI general (PhotoStudio).**
- Layout: izquierda catálogo (miniaturas, filtros por categoría, búsqueda); centro editor; derecha panel del mueble seleccionado
  (nombre, medidas, rotación, modo 3D/recorte si ambos existen, borrar) + toggles (oclusión, máscara de piso, sombras, intensidad de sombra, exposición de muebles 0.5–1.5).
- Barra superior: "Subir foto", lista de escenas previas, "Exportar PNG". Estados de carga con mensajes ("Analizando la foto… (~10–30 s)").
- Errores de backend visibles en un toast en español.

🛑 **PARAR Y PREGUNTAR (fin Fase 2):** crea el primer release (ver 7.1) y entrega a Gabriela:
3 PNG exportados con sus fotos, la lista de muebles del catálogo semilla y cómo probar.
Preguntas: (1) "¿Los muebles se ven del tamaño correcto y apoyados en el piso?" (2) "¿Cambias algo del diseño/flujo?"
(3) "¿Qué muebles quieres en el catálogo semilla (quitar/agregar)?" (4) "¿Le enviamos este release a tu hermano ya?"

---

### FASE 3 — Sugerencia inteligente de ubicación

**3.1 Grilla de ocupación (`geometry/occupancy.py`).**
- Transformar los puntos del piso al mundo del piso (inversa de `floor_frame`). Grilla de **10 cm** en x/z.
- Estados por celda: `free` (tiene puntos de piso), `blocked` (tiene puntos a altura 0.05–1.8 m sobre el piso: objetos/paredes),
  `unknown` (sin datos). Celdas `free` a < 20 cm de `blocked` → `near_obstacle`.
- **Borde de pared:** celdas `free` adyacentes a `blocked` cuya altura máxima de puntos vecinos > 1.2 m → `wall_edge`,
  guardando la dirección hacia la pared (vector normal horizontal).
- Descartar celdas cuya proyección caiga fuera de la imagen (no son "pared", son borde del encuadre).
- Guardar `occupancy.png` de debug (vista cenital coloreada).

**3.2 Heurística (`placement/heuristic.py`).** Greedy, muebles ordenados de mayor a menor área:
- `against_wall=true`: candidatos = celdas `wall_edge`; orientación = frente mirando **lejos de la pared**; el fondo del mueble a 5 cm de la pared.
- `rug`, `coffee_table`, `dining_table`: candidatos = centroide de la zona libre más grande, o frente al sofá ya colocado
  (mesa de centro a 45 cm del frente del sofá, alineada).
- `chair`: alrededor de `dining_table`/`desk` si existe; si no, junto a pared.
- `lamp`, `plant`: esquinas (celdas `wall_edge` con dos paredes cerca) o al lado del sofá.
- Validación de cada candidato: la huella rotada (width × depth) cae **toda** en celdas `free`/`near_obstacle`, no se cruza
  con muebles ya ubicados (+10 cm de holgura), y sus 4 esquinas + la esquina superior proyectan **dentro de la imagen**.
- Puntaje = 0.4·visibilidad (fracción de huella visible) + 0.3·(distancia a cámara en 2–5 m) + 0.3·regla de categoría.
- Devolver `placements` con `source:"heuristic"` y `notes` legibles ("El sofá va contra la pared del fondo").

**3.3 VLM local opcional (`placement/vlm.py`).**
- Si `OLLAMA_URL` responde (`GET /api/tags`) y existe el modelo `qwen3-vl:4b-instruct` (configurable `VLM_MODEL`):
  dibujar sobre la foto los **top 8 candidatos** por mueble como círculos numerados, enviar imagen + instrucción
  (en inglés al modelo, respuesta JSON `{ "choices": [{"item_id":..., "candidate": n, "reason": "..."}] }`) usando
  `POST /api/chat` con `format: "json"` y `stream:false`, timeout 120 s.
- Validar el JSON; si falla o timeout → usar la heurística y agregar nota "La IA local no respondió; se usó la sugerencia básica".
- El VLM **solo elige entre candidatos válidos**; nunca inventa coordenadas.

**3.4 UI.** Botón "Sugerir ubicación" (para los muebles seleccionados en el catálogo o los ya puestos) con switch "Usar IA local (Ollama)"
deshabilitado con tooltip si Ollama no está. Las sugerencias aparecen como "fantasmas" (semitransparentes) con botones
"Aceptar todas" / "Aceptar" / "Descartar". Mostrar las `notes`.

**3.5 Tests.** Grillas sintéticas (habitación rectangular 4×5 m con cámara en un lado) → el sofá queda contra una pared y la
mesa de centro frente al sofá; ningún mueble se solapa. e2e: botón sugerir produce ≥ 1 fantasma.

**3.6 Leer la tabla de medidas automáticamente (muebles nuevos desde la UI).**
- Si el usuario sube una foto de la tabla en `CatalogAdmin`, `POST /api/catalog/extract-dimensions` la envía al VLM local
  (Ollama, `qwen3-vl:4b-instruct`) pidiendo JSON `{ "raw_table": {...}, "width_cm", "depth_cm", "height_cm", "extra_dimensions_cm": {...}, "units_detected" }`
  con las reglas de §5.2 incluidas en el prompt.
- Validar (pydantic + rangos) y **prellenar** el formulario; el usuario confirma o corrige antes de guardar
  (`dimensions_source: "vlm_extraida"`, `dimensions_verified: true` solo al confirmar).
- Sin Ollama → el formulario se llena a mano (nunca bloquear).
- Test: correr la extracción sobre las tablas de `samples/furniture/*/medidas.*` y comparar con los `mueble.json` verificados;
  reportar aciertos en PROGRESO (tolerancia ±1 cm).

🛑 **PARAR Y PREGUNTAR (fin Fase 3):** muestra 3 ejemplos (sugerencia básica vs. con IA local si está instalada, con tiempos).
Incluye el % de aciertos de 3.6. Pregunta: "¿Las ubicaciones tienen sentido? ¿Vale la pena la IA local (tarda X s) o dejamos solo la básica?"

---

### FASE 4 — Retoque (clásico local + IA opcional)

**4.1 Retoque clásico (frontend, siempre disponible).**
- "Ajuste automático de luz": calcular luminancia media y color medio de la foto en la zona de piso (usar `floor_mask_png`);
  mapear a `hemisphereLight` (color y 0.5–1.2 de intensidad) y a la exposición de los muebles; slider manual para corregir.
- Dirección de luz: slider de ángulo (0–360°) y altura para la `directionalLight`; valor por defecto desde arriba-atrás de la cámara.
- Suavizado de bordes: exportar a 2× y reducir (supersampling) en `exportImage.ts`.

**4.2 Proveedor IA (`providers/hf_edit.py`).**
- `gradio_client.Client("Qwen/Qwen-Image-Edit-2511", hf_token=HF_TOKEN)` (Space configurable en `.env`: `HF_EDIT_SPACE`).
  **Primero inspecciona** con `client.view_api()` y documenta en el archivo qué endpoint y parámetros usas.
  Si ese Space no existe o cambió, busca en Hugging Face otro Space oficial de Qwen-Image-Edit y 🛑 pregunta antes de usar uno de terceros.
- Entrada: `composite.png` (redimensionado a máx. 1024 px). Prompt fijo (en inglés):
  *"Make the lighting, shadows and reflections of the furniture consistent with the room. Keep the furniture's shape, color, texture and position exactly the same. Do not add or remove objects. Keep the camera and room unchanged."*
- **Conservar mueble exacto** (default ON): después de la IA, pegar encima los píxeles originales del mueble usando la máscara
  (difuminada 3 px). Así la IA solo mejora el contexto (sombras, luz en el piso/pared) y el mueble queda idéntico.
- Control de fidelidad (si keep_furniture=OFF): diferencia media absoluta dentro de la máscara > 0.12 → aviso
  "⚠️ La IA alteró el mueble".
- Errores: sin token → mensaje "Configura HF_TOKEN en .env (gratis)"; cuota agotada → "Se acabó la cuota gratis de hoy; usa el retoque clásico".
- `POST /api/scenes/{id}/retouch` devuelve el PNG; guardar en `data/scenes/<id>/retouch_<n>.png`.

**4.3 UI.** Panel "Retoque": botón "Mejorar con IA (gratis, cuota diaria)", switch "Conservar mueble exacto",
comparador antes/después (slider), botón "Descargar". Aviso: "La imagen se envía a Hugging Face para procesarla".

🛑 **PARAR Y PREGUNTAR (fin Fase 4):** muestra 2–3 pares antes/después y el tiempo/cuota consumida.
Pregunta: "¿La mejora vale la pena? ¿Dejamos el botón de IA visible?"

---

### FASE 5 — Video

**Advertencia para expectativas (dísela a Gabriela en el checkpoint):** el seguimiento de cámara falla en paredes
blancas lisas. Para mejores resultados: video horizontal, 10–20 s, movimiento lento, que se vean piso, puertas y ventanas.

**5.1 v0 — Video a fotogramas clave (rápido y robusto).**
- `POST /api/videos` guarda el video (máx. 60 s, 300 MB). `video/keyframes.py` con `imageio-ffmpeg`/`imageio`:
  extraer a 5 fps, dividir en N ventanas (default 6), elegir en cada ventana el frame más nítido (varianza del Laplaciano).
- `POST /api/videos/{id}/keyframes` crea N escenas de foto (reutiliza Fase 1) → el usuario amobla cada una en el PhotoStudio.
- **Medidas del espacio desde el video:** mostrar el `room_estimate` de cada fotograma y un resumen = mediana de altura de techo y
  el mayor ancho/fondo visibles (con la nota de que son aproximados). En 5.2 (SfM) se puede mejorar uniendo el piso de varios frames
  en el mundo métrico; hazlo solo si Gabriela lo pide en el 🛑.
- UI: página VideoStudio con la tira de fotogramas y botón "Amoblar este fotograma".

**5.2 v1 — Seguimiento de cámara (SfM) con pycolmap.** (Solo después del 🛑 de 5.1.)
- Extraer frames a **5 fps**, redimensionados a 960 px lado largo, en `data/videos/<id>/frames_sfm/`.
- pycolmap: `extract_features` (SIFT, cámara única `SIMPLE_PINHOLE`), `match_sequential` (overlap 10),
  `incremental_mapping`. Usar el modelo reconstruido más grande. Si registra < 70 % de frames → error en español con los consejos de grabación.
- Poses: para cada imagen, `world_from_cam = inverse(cam_from_world)` (convención OpenCV).
  Cámara three: `M_three = world_from_cam_cv · diag(1,−1,−1,1)`.
- **Escala métrica:** frame de referencia r (el primero registrado con más puntos 3D). Correr MoGe en r; para cada punto 3D
  de COLMAP visible en r: `ratio = profundidad_MoGe(pixel) / profundidad_COLMAP`. `s = mediana(ratios)` (mínimo 30 puntos).
  Multiplicar todas las traslaciones y puntos de COLMAP por `s`.
- **Piso en el mundo:** calcular `floor_frame_r` con MoGe en el frame r (igual que en fotos, coords three de la cámara r) y
  llevarlo al mundo: `floor_frame_world = M_three(r) · floor_frame_r` (ya todo en metros tras aplicar `s`).
- **Interpolar poses** a la tasa final (**15 fps**): lerp de posición y slerp de rotación entre frames registrados.
- Guardar `track.json`: `{fps, width, height, fov_y_deg, frames:[{index, image_url, matrix_world[16]}], floor_frame[16], ref_index}`.
- Test: video sintético (render de una escena simple con cámara conocida, generado con trimesh/pyrender o con el propio three en Playwright)
  → error de pose relativo < 5 %. Si es muy difícil, 🛑 pregunta si basta con prueba manual.

**5.3 Render del video (frontend + backend).**
- VideoStudio: el Editor3D recibe `camera.matrix_world` del frame de referencia y el `floor_frame` del mundo → el usuario ubica muebles
  (sin oclusión en v1).
- "Renderizar video": para cada frame, fijar la cámara, cambiar la foto de fondo, componer como en `exportImage.ts` y subir el PNG
  en lotes (`POST /api/videos/{id}/render`). Barra de progreso.
- Backend codifica con ffmpeg (imageio-ffmpeg): `-framerate 15 -c:v libx264 -pix_fmt yuv420p -crf 20` → `amoblado.mp4`.
- ✅ Verificar: e2e con `samples/videos/<primero>` y revisar 3 frames del MP4 (extraer con ffmpeg y mirarlos).

🛑 **PARAR Y PREGUNTAR** (dos momentos):
- Tras 5.1: "¿Te sirve amoblar fotogramas del video, o seguimos con el video en movimiento (5.2–5.3, más complejo y menos robusto)?"
- Tras 5.3: muestra el MP4. "¿Se ven los muebles pegados al piso mientras la cámara se mueve? ¿Necesitamos oclusión en video?"

---

### FASE 6 — Foto de mueble → modelo 3D (opcional)

**6.1 Proveedor (`providers/hf_3d.py`).** `gradio_client` contra `microsoft/TRELLIS.2` (configurable `HF_3D_SPACE`); fallback a un Space
de TripoSR. **Inspecciona la API primero** (`view_api`). Entrada: `cutout.png`. Salida: GLB.
**6.2 Normalización.** Recentrar, apoyar en y=0, escala uniforme por el ancho declarado, orientar frente a +z
(si queda mal, el usuario corrige con `yaw_offset_deg` desde la UI). Comprimir con gltf-transform (< 8 MB).
**6.3 UI.** En CatalogAdmin: botón "Generar 3D (gratis, tarda 1–3 min)" → job con progreso → visor con órbita para aprobar →
"Usar 3D" cambia `preferred_mode` a `3d`. Siempre se puede volver a "recorte".

🛑 **PARAR Y PREGUNTAR:** muestra 2 muebles generados junto a su foto. "¿La calidad del 3D sirve para mostrar el mueble real, o preferimos el recorte 2D?"

---

### FASE 7 — Empaquetado para compartir (sin deploy)

**7.1 Release zip (`scripts/crear_release.sh`).**
- Correr `build_frontend.sh`; copiar el repo a `release/santiago-muebles-v<versión>/` **excluyendo**: `.git`, `node_modules`,
  `frontend/` (no hace falta: el build ya está en `backend/app/static`), `.venv`, `data/scenes`, `data/videos`, `.env`, `samples/`.
- Incluir `LEEME_PRIMERO.txt` (español, para Windows y Mac):
  1. Descomprime la carpeta. 2. Windows: doble clic en `scripts\windows\iniciar.bat` (si aparece "Windows protegió su PC" →
  "Más información" → "Ejecutar de todas formas"). Mac: clic derecho en `scripts/mac/iniciar.command` → Abrir.
  3. La primera vez descarga ~2–3 GB (Python, librerías, modelos) y tarda 5–15 min. 4. Se abre el navegador en `http://localhost:8000`.
  5. Para cerrar, cierra la ventana negra (consola). 6. Opcional: IA de retoque → crear token en huggingface.co y pegarlo en `.env`.
- Generar `release/santiago-muebles-v<versión>.zip`. Versionado semántico en `backend/app/__init__.py`.
- ✅ Verificar: descomprimir el zip en una carpeta temporal y arrancar desde ahí en el Mac; la CI de Windows (0.5) debe correr también un job que descargue
  el artefacto del zip y ejecute `instalar.bat` + health check (agregar job `release-smoke` en `workflow_dispatch`).

**7.2 Demo en vivo temporal (opcional).** Documentar en README: `brew install cloudflared` y
`cloudflared tunnel --url http://localhost:8000` genera un enlace público temporal mientras el Mac esté encendido.
Advertencia: cualquiera con el enlace entra; cerrar el túnel al terminar. **No** automatizar esto.

---

## 7. Criterios de "terminado" del MVP (Fases 0–4)
- En el Mac de Gabriela y en Windows (CI) la app arranca con un doble clic.
- Todos los muebles de Gabriela están en el catálogo con medidas verificadas en cm.
- Con una foto de un espacio vacío: se detecta el piso, se estiman las medidas del espacio (sin que el usuario las dé),
  se ponen ≥ 3 muebles del catálogo **a escala real** (cuadrícula de 1 m creíble, aviso si no caben),
  sombras, se sugieren ubicaciones, se exporta PNG, y (con token) se retoca con IA conservando el mueble.
- Tests: `uv run pytest -q` y `npm run test` verdes; e2e principal verde.

---

## 8. Cuándo PARAR y preguntar a Gabriela (además de los 🛑 de cada fase)
Pregunta SIEMPRE antes de:
1. Agregar una dependencia, modelo o asset con licencia fuera de §0.7, o cualquier servicio que pida tarjeta/pago.
2. Pedir o usar una API key/token nuevo (distinto de `HF_TOKEN`).
3. Cambiar una decisión de §2 (stack, modelos) o la estructura de §3.
4. Borrar datos de `data/` o `samples/`, o reescribir historial de git (`push --force`, `rebase` de `main`).
5. Cuando un paso tarde más de lo esperado de forma repetida (p. ej. análisis de foto > 90 s en el Mac).
6. Cuando tras 2 intentos un error siga igual.
7. Cuando el plan sea ambiguo o contradiga lo que ves en el código.

**Formato de la pregunta** (corto, en español):
```
## Estado: Fase X.Y
Hecho: <3–5 viñetas>
Cómo probarlo: <comandos exactos o pasos de clic>
Evidencia: <rutas a capturas/PNGs>
Pregunta: <una pregunta concreta con opciones A/B/C y tu recomendación>
```

---

## 9. Plantilla de `PROGRESO.md`
```markdown
# Progreso — Estudio Virtual
Versión actual: 0.0.0 · Última actualización: <fecha>

## Fase 0
- [ ] 0.1 Repo y documentos base — nota:
- [ ] 0.2 Backend mínimo — nota:
...
## Decisiones tomadas con Gabriela
- <fecha>: <decisión>
## Problemas abiertos
- <descripción, qué se intentó>
## Mediciones
| Foto | Dispositivo | Tiempo análisis | Altura cámara | % piso |
```

---

## 10. Riesgos conocidos y plan B
| Riesgo | Señal | Plan B |
|---|---|---|
| MoGe falla en MPS | error de operador en `mps` | forzar `DEVICE=cpu` (más lento pero funciona) |
| Escala métrica errada (±10–20 %) | muebles se ven gigantes/pequeños, cuadrícula no parece de 1 m | calibración manual (2.8); probar `moge-2-vitl-normal` |
| Tabla de medidas ambigua o mal transcrita | ancho y fondo invertidos, proporción foto≠tabla | chequeo de proporción (0.6) y 🛑 preguntar |
| Piso no detectado (fotos muy cerradas, piso tapado) | `piso_no_encontrado` | piso manual (2.9) |
| Recorte 2D se ve "pegado" | el ángulo de la foto del mueble no coincide con la del cuarto | pedir foto del mueble a la altura de la cámara; o Fase 6 (3D) |
| Cuota ZeroGPU agotada / cuenta HF con < 30 días | error de cuota | retoque clásico; reintentar al día siguiente |
| SfM falla en paredes blancas | < 70 % frames registrados | usar v0 (fotogramas clave) |
| Windows sin Git | falla `uv sync` en dependencia git | URLs zip (0.4); último recurso: `winget install Git.Git` en `instalar.bat` |
| Descargas lentas la 1.ª vez | instalación > 15 min | `instalar.*` muestra progreso y se puede reintentar sin perder lo descargado |

## 11. Ideas futuras (NO implementar ahora)
AR en vivo desde el celular (WebXR / Quick Look con USDZ), oclusión en video, multi-habitación, cotizador de arriendo
(depreciación + margen), login y marketplace.
