import { describe, expect, it } from 'vitest'
import type { CatalogItem } from './api/client'
import { billboardSize, formatDims } from './catalog'

const base = {
  dimensions_cm: { width: 200, depth: 90, height: 80 },
  cutout_ratio: 2.4,
} as CatalogItem

describe('formatDims', () => {
  it('ancho × fondo × alto en cm', () => {
    expect(formatDims({ width: 210, depth: 90, height: 85 })).toBe('210 × 90 × 85 cm')
    expect(formatDims({ width: 181.3, depth: 82, height: 71.0 })).toBe('181.3 × 82 × 71 cm')
  })
})

describe('billboardSize', () => {
  it('usa las medidas de la tabla si la proporción coincide', () => {
    expect(billboardSize(base)).toEqual({ width: 2, height: 0.8 })
  })
  it('conserva la proporción de la foto ajustada al alto si difiere > 15 %', () => {
    const s = billboardSize({ ...base, cutout_ratio: 1.5 })
    expect(s.height).toBe(0.8)
    expect(s.width).toBeCloseTo(1.2)
  })
  it('sin recorte usa la tabla', () => {
    expect(billboardSize({ ...base, cutout_ratio: null })).toEqual({ width: 2, height: 0.8 })
  })
})
