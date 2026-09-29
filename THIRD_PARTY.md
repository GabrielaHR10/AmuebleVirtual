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
| onnxruntime | librería | https://github.com/microsoft/onnxruntime | MIT | Ejecuta los modelos de recorte |

**No usado por licencia:** `pillow-heif` (el plan lo pedía para HEIC) — sus wheels traen x265 y quedan **GPLv2**.
Decisión de Gabriela (2026-09-28): solo JPG/PNG.

## Material de prueba
Las fotos de muebles de tiendas en `samples/furniture/` son **solo para pruebas internas**: no se publican
ni se incluyen en el release.
