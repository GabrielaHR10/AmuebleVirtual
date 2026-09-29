import { Matrix4, Vector3 } from 'three'
import type { CatalogItem, Placement } from '../api/client'
import { footprintCorners, polygonsOverlap, projectFloorPoint } from './math'

export interface MaskData {
  width: number
  height: number
  data: Uint8ClampedArray // RGBA; blanco = piso
}

export interface FitContext {
  mask: MaskData | null
  frame: Matrix4
  cameraWorld: Matrix4
  intrinsics: number[][]
  scaleK: number
}

export interface FitResult {
  ok: boolean
  message: string | null
}

const OUTSIDE_LIMIT = 0.1
const SAMPLES = 8

export function footprintOf(p: Placement, item: CatalogItem, scaleK: number) {
  const w = (item.dimensions_cm.width / 100) * scaleK
  const d = (item.dimensions_cm.depth / 100) * scaleK
  return footprintCorners(p.x, p.z, w, d, p.yaw_deg)
}

/** Fracción de la huella que cae fuera del piso visible (según floor_mask.png). */
export function outsideFraction(p: Placement, item: CatalogItem, ctx: FitContext): number {
  const { mask } = ctx
  if (!mask) return 0
  const w = (item.dimensions_cm.width / 100) * ctx.scaleK
  const d = (item.dimensions_cm.depth / 100) * ctx.scaleK
  const a = (p.yaw_deg * Math.PI) / 180
  const c = Math.cos(a)
  const s = Math.sin(a)
  let outside = 0
  let total = 0
  for (let i = 0; i < SAMPLES; i++) {
    for (let j = 0; j < SAMPLES; j++) {
      const lx = ((i + 0.5) / SAMPLES - 0.5) * w
      const lz = ((j + 0.5) / SAMPLES - 0.5) * d
      const pt = new Vector3(p.x + lx * c + lz * s, 0, p.z - lx * s + lz * c)
      const uv = projectFloorPoint(pt, ctx.frame, ctx.cameraWorld, ctx.intrinsics)
      total += 1
      if (!uv || uv[0] < 0 || uv[0] >= 1 || uv[1] < 0 || uv[1] >= 1) {
        outside += 1
        continue
      }
      const px = Math.floor(uv[0] * mask.width)
      const py = Math.floor(uv[1] * mask.height)
      if (mask.data[(py * mask.width + px) * 4] < 128) outside += 1
    }
  }
  return outside / total
}

/** ¿Cabe el mueble? Rojo si > 10 % queda fuera del piso visible o si se cruza con otro (PLAN 2.7). */
export function fitStatus(
  p: Placement,
  item: CatalogItem,
  others: { p: Placement; item: CatalogItem }[],
  ctx: FitContext,
): FitResult {
  if (outsideFraction(p, item, ctx) > OUTSIDE_LIMIT) {
    return { ok: false, message: 'No cabe aquí: parte del mueble queda fuera del piso visible' }
  }
  if (item.category !== 'rug') {
    const mine = footprintOf(p, item, ctx.scaleK)
    for (const o of others) {
      if (o.p.uid === p.uid || o.item.category === 'rug') continue
      if (polygonsOverlap(mine, footprintOf(o.p, o.item, ctx.scaleK))) {
        return { ok: false, message: `Se cruza con ${o.item.name}` }
      }
    }
  }
  return { ok: true, message: null }
}

/**
 * Primer lugar libre en espiral alrededor de (x0, z0) donde el mueble cabe sin cruzarse con otros.
 * Si no hay ninguno dentro del piso visible, busca al menos uno sin cruces; si tampoco, el punto inicial.
 */
export function findFreeSpot(
  x0: number,
  z0: number,
  item: CatalogItem,
  others: { p: Placement; item: CatalogItem }[],
  ctx: FitContext,
): [number, number] {
  const probe = (x: number, z: number): Placement => ({
    uid: '__probe__', item_id: item.id, mode: 'cutout', x, z, yaw_deg: 0, source: 'manual',
  })
  const step = 0.3
  for (const c of [ctx, { ...ctx, mask: null }]) {
    for (let ring = 0; ring <= 10; ring++) {
      const n = ring === 0 ? 1 : ring * 8
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2
        const x = x0 + Math.cos(a) * ring * step
        const z = z0 + Math.sin(a) * ring * step
        if (fitStatus(probe(x, z), item, others, c).ok) return [x, z]
      }
    }
  }
  return [x0, z0]
}
