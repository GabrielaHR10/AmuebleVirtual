# Terceros: modelos, assets y licencias

Solo se permiten licencias MIT, Apache-2.0, BSD, CC0 y CC-BY (ver PLAN §0.7).
Cada modelo o asset que use el proyecto se registra aquí.

| Nombre | Tipo | URL | Licencia | Uso en el proyecto |
|---|---|---|---|---|
| MoGe (código, commit `925b8ed`, última versión MoGe-2) | librería | https://github.com/microsoft/MoGe | MIT (+ partes Apache-2.0) | Geometría métrica de la foto |
| `Ruicheng/moge-2-vitb-normal` | pesos de modelo | https://huggingface.co/Ruicheng/moge-2-vitb-normal | MIT | Modelo por defecto de MoGe-2 |
| utils3d (commit `3fab839`) | librería | https://github.com/EasternJournalist/utils3d | MIT | Dependencia de MoGe |
| pipeline (commit `866f059`) | librería | https://github.com/EasternJournalist/pipeline | MIT | Dependencia de MoGe |
| rembg | librería | https://github.com/danielgatis/rembg | MIT | Quitar el fondo a fotos de muebles |
| BiRefNet (`birefnet-general-lite`) | pesos de modelo | https://github.com/ZhengPeng7/BiRefNet | MIT | Modelo de recorte principal |
| IS-Net (`isnet-general-use`) | pesos de modelo | https://github.com/xuebinqin/DIS | Apache-2.0 | Modelo de recorte de respaldo |
| Poly Haven `sofa_02` | modelo 3D | https://polyhaven.com/a/sofa_02 | CC0 | Catálogo semilla |
| Poly Haven `sofa_03` | modelo 3D | https://polyhaven.com/a/sofa_03 | CC0 | Catálogo semilla |
| Poly Haven `modern_arm_chair_01` | modelo 3D | https://polyhaven.com/a/modern_arm_chair_01 | CC0 | Catálogo semilla |
| Poly Haven `mid_century_lounge_chair` | modelo 3D | https://polyhaven.com/a/mid_century_lounge_chair | CC0 | Catálogo semilla |
| Poly Haven `modern_coffee_table_01` | modelo 3D | https://polyhaven.com/a/modern_coffee_table_01 | CC0 | Catálogo semilla |
| Poly Haven `coffee_table_round_01` | modelo 3D | https://polyhaven.com/a/coffee_table_round_01 | CC0 | Catálogo semilla |
| Poly Haven `round_wooden_table_01` | modelo 3D | https://polyhaven.com/a/round_wooden_table_01 | CC0 | Catálogo semilla |
| Poly Haven `dining_chair_02` | modelo 3D | https://polyhaven.com/a/dining_chair_02 | CC0 | Catálogo semilla |
| Poly Haven `modern_wooden_cabinet` | modelo 3D | https://polyhaven.com/a/modern_wooden_cabinet | CC0 | Catálogo semilla |
| Poly Haven `wooden_display_shelves_01` | modelo 3D | https://polyhaven.com/a/wooden_display_shelves_01 | CC0 | Catálogo semilla |
| Poly Haven `side_table_01` | modelo 3D | https://polyhaven.com/a/side_table_01 | CC0 | Catálogo semilla |
| Poly Haven `potted_plant_02` | modelo 3D | https://polyhaven.com/a/potted_plant_02 | CC0 | Catálogo semilla |
| glTF-Transform CLI | herramienta (solo al crear el catálogo) | https://gltf-transform.dev | MIT | Convertir/optimizar GLB |
| onnxruntime | librería | https://github.com/microsoft/onnxruntime | MIT | Ejecuta los modelos de recorte |

**No usado por licencia:** `pillow-heif` (el plan lo pedía para HEIC) — sus wheels traen x265 y quedan **GPLv2**.
Decisión de Gabriela (2026-09-28): solo JPG/PNG.

## Material de prueba
Las fotos de muebles de tiendas en `samples/furniture/` son **solo para pruebas internas**: no se publican
ni se incluyen en el release.
