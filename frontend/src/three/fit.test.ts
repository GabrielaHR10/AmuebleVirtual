import { Matrix4, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import type { CatalogItem, Placement } from '../api/client'
import { findFreeSpot, fitStatus, type FitContext, type MaskData } from './fit'
import { floorFrameFromPlane } from './math'

const K = [
  [0.9, 0, 0.5],
  [0, 0.7, 0.5],
  [0, 0, 1],
]
const a = (25 * Math.PI) / 180
const frame = floorFrameFromPlane(new Vector3(0, Math.cos(a), Math.sin(a)), 1.4)

/** Máscara: piso solo en la mitad inferior de la imagen. */
function halfMask(): MaskData {
  const width = 100
  const height = 100
  const data = new Uint8ClampedArray(width * height * 4)
  for (let y = 50; y < height; y++) for (let x = 0; x < width; x++) data[(y * width + x) * 4] = 255
  return { width, height, data }
}

const ctx: FitContext = { mask: halfMask(), frame, cameraWorld: new Matrix4(), intrinsics: K, scaleK: 1 }
const sofa = { id: 'sofa', name: 'Sofá', category: 'sofa', dimensions_cm: { width: 200, depth: 90, height: 80 } } as CatalogItem
const rug = { id: 'rug', name: 'Tapete', category: 'rug', dimensions_cm: { width: 200, depth: 150, height: 1 } } as CatalogItem
const at = (uid: string, item: string, x: number, z: number): Placement => ({
  uid, item_id: item, mode: 'cutout', x, z, yaw_deg: 0, source: 'manual',
})

describe('fitStatus', () => {
  it('cabe cerca de la cámara (piso visible)', () => {
    expect(fitStatus(at('a', 'sofa', 0, -2.5), sofa, [], ctx)).toEqual({ ok: true, message: null })
  })
  it('no cabe lejos (fuera de la máscara)', () => {
    const r = fitStatus(at('a', 'sofa', 0, -9), sofa, [], ctx)
    expect(r.ok).toBe(false)
    expect(r.message).toContain('No cabe')
  })
  it('se cruza con otro mueble, pero no con un tapete', () => {
    const other = { p: at('b', 'sofa', 1, -2.5), item: sofa }
    expect(fitStatus(at('a', 'sofa', 0, -2.5), sofa, [other], ctx).message).toBe('Se cruza con Sofá')
    const onRug = { p: at('c', 'rug', 0, -2.5), item: rug }
    expect(fitStatus(at('a', 'sofa', 0, -2.5), sofa, [onRug], ctx).ok).toBe(true)
  })
})

describe('findFreeSpot', () => {
  it('corre el mueble nuevo para que no se cruce con uno existente', () => {
    const other = { p: at('b', 'sofa', 0, -2.5), item: sofa }
    const [x, z] = findFreeSpot(0, -2.5, sofa, [other], ctx)
    expect(fitStatus(at('a', 'sofa', x, z), sofa, [other], ctx).ok).toBe(true)
  })
  it('si el lugar ya está libre, no lo mueve', () => {
    expect(findFreeSpot(0, -2.5, sofa, [], ctx)).toEqual([0, -2.5])
  })
})
