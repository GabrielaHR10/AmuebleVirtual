import { describe, expect, it } from 'vitest'
import type { Scene } from '../api/client'
import { autoLight, lightPosition } from './lighting'

const scene = (l: Scene['lighting']) => ({ lighting: l }) as Scene

describe('autoLight', () => {
  it('la luz viene de la ventana del fondo', () => {
    const s = autoLight(scene({ floor_rgb: [131, 120, 116], floor_luminance: 0.2, light_source: [0.25, 2.1, -5.2] }), [0, 0, -3])
    expect(s.azimuth < 10 || s.azimuth > 350).toBe(true)
    const [, y, z] = lightPosition(s, [0, 0, -3])
    expect(z).toBeLessThan(-3) // la luz está hacia el fondo: las sombras caen hacia la cámara
    expect(y).toBeGreaterThan(2)
  })
  it('piso cálido → luz ambiente cálida; foto oscura → menos exposición', () => {
    const s = autoLight(scene({ floor_rgb: [128, 101, 82], floor_luminance: 0.1, light_source: null }), [0, 0, -3])
    expect(s.hemiColor).toBe('#ffe9da')
    expect(s.exposure).toBeLessThan(1)
  })
  it('sin datos usa la luz por defecto', () => {
    expect(autoLight(scene(null), [0, 0, -3]).hemiIntensity).toBe(0.8)
  })
})
