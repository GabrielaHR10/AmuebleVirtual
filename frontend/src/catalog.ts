import type { CatalogItem, Category, Dimensions } from './api/client'

export const CATEGORY_LABELS: Record<Category, string> = {
  sofa: 'Sofá',
  armchair: 'Sillón',
  chair: 'Silla',
  bed: 'Cama',
  nightstand: 'Mesa de noche / auxiliar',
  dining_table: 'Mesa de comedor',
  coffee_table: 'Mesa de centro',
  desk: 'Escritorio',
  tv_stand: 'Mueble de TV',
  shelf: 'Estantería',
  wardrobe: 'Clóset',
  rug: 'Tapete',
  lamp: 'Lámpara',
  plant: 'Planta',
  other: 'Otro',
}

/** "210 × 90 × 85 cm" (ancho × fondo × alto). */
export function formatDims(d: Dimensions): string {
  const n = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1).replace(/\.0$/, ''))
  return `${n(d.width)} × ${n(d.depth)} × ${n(d.height)} cm`
}

export function thumbOf(item: CatalogItem): string | null {
  return item.thumb_url ?? item.cutout_url ?? item.photo_url
}

/** Tamaño del recorte 2D en metros (PLAN 2.5): tabla si la proporción coincide (≤ 15 %), si no, foto ajustada al alto. */
export function billboardSize(item: CatalogItem): { width: number; height: number } {
  const { width, height } = item.dimensions_cm
  const w = width / 100
  const h = height / 100
  const ratio = item.cutout_ratio
  if (!ratio || Math.abs(ratio - w / h) / (w / h) <= 0.15) return { width: w, height: h }
  return { width: h * ratio, height: h }
}
