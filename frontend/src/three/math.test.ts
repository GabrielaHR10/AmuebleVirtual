import { Matrix4, Vector3 } from 'three'
import { describe, expect, it } from 'vitest'
import {
  dropPoint,
  floorFrameFromPlane,
  footprintCorners,
  planeFromPoints,
  polygonsOverlap,
  projectFloorPoint,
} from './math'

const I = new Matrix4()
const K = [
  [0.78, 0, 0.5],
  [0, 1.04, 0.5],
  [0, 0, 1],
]

// Mismos casos que backend/tests/test_coords.py
describe('floorFrameFromPlane', () => {
  it('plano sintético nivelado', () => {
    const m = floorFrameFromPlane(new Vector3(0, 1, 0), 1.5)
    const e = m.elements // column-major
    const close = (got: number[], want: number[]) => want.forEach((w, i) => expect(got[i]).toBeCloseTo(w))
    close(e.slice(12, 15), [0, -1.5, 0])
    close(e.slice(0, 3), [1, 0, 0])
  })
  it('cámara inclinada: det = +1 y x hacia la derecha', () => {
    const a = (20 * Math.PI) / 180
    const m = floorFrameFromPlane(new Vector3(0, Math.cos(a), Math.sin(a)), 1.4)
    expect(m.determinant()).toBeCloseTo(1)
    expect(m.elements[0]).toBeGreaterThan(0)
    const cam = new Vector3().applyMatrix4(m.clone().invert())
    expect(cam.y).toBeCloseTo(1.4)
  })
  it('d negativo se invierte', () => {
    const a = floorFrameFromPlane(new Vector3(0, 1, 0), 1.5)
    const b = floorFrameFromPlane(new Vector3(0, -1, 0), -1.5)
    expect(a.equals(b)).toBe(true)
  })
})

describe('planeFromPoints', () => {
  it('plano del piso a 1.2 m', () => {
    const { normal, d } = planeFromPoints(new Vector3(0, -1.2, -1), new Vector3(1, -1.2, -2), new Vector3(-1, -1.2, -3))
    expect(normal.y).toBeCloseTo(1)
    expect(d).toBeCloseTo(1.2)
  })
})

describe('projectFloorPoint', () => {
  it('un punto del piso delante de la cámara cae en la mitad inferior', () => {
    const m = floorFrameFromPlane(new Vector3(0, 1, 0), 1.5)
    const uv = projectFloorPoint(new Vector3(0, 0, -3), m, I, K)!
    expect(uv[0]).toBeCloseTo(0.5)
    expect(uv[1]).toBeCloseTo(0.5 + (1.04 * 1.5) / 3)
    expect(projectFloorPoint(new Vector3(0, 0, 2), m, I, K)).toBeNull()
  })
})

describe('huellas', () => {
  it('rotar 90° intercambia ancho y fondo', () => {
    const c = footprintCorners(0, 0, 2, 1, 90)
    const xs = c.map((p) => p[0])
    const zs = c.map((p) => p[1])
    expect(Math.max(...xs) - Math.min(...xs)).toBeCloseTo(1)
    expect(Math.max(...zs) - Math.min(...zs)).toBeCloseTo(2)
  })
  it('detecta cruces', () => {
    const a = footprintCorners(0, 0, 2, 1, 0)
    expect(polygonsOverlap(a, footprintCorners(1.5, 0, 2, 1, 0))).toBe(true)
    expect(polygonsOverlap(a, footprintCorners(2.5, 0, 2, 1, 0))).toBe(false)
    expect(polygonsOverlap(a, footprintCorners(1.6, 0.9, 1, 1, 45))).toBe(false)
  })
})

describe('dropPoint', () => {
  it('cámara inclinada: el centro de la imagen toca el piso delante', () => {
    const a = (25 * Math.PI) / 180
    const m = floorFrameFromPlane(new Vector3(0, Math.cos(a), Math.sin(a)), 1.5)
    const p = dropPoint(m, I)
    expect(p.y).toBe(0)
    expect(p.z).toBeCloseTo(-1.5 / Math.tan(a), 5)
  })
  it('cámara horizontal: 3 m delante', () => {
    const m = floorFrameFromPlane(new Vector3(0, 1, 0), 1.5)
    const p = dropPoint(m, I)
    expect(p.z).toBeCloseTo(-3)
  })
})
