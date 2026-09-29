import { beforeEach, describe, expect, it } from 'vitest'
import type { CatalogItem } from '../api/client'
import {
  acceptGhosts,
  addPlacement,
  duplicatePlacement,
  removePlacement,
  scaleFromCalibration,
  updatePlacement,
  useStudio,
} from './useStudio'

const sofa = { id: 'sofa', preferred_mode: 'cutout', glb_url: null } as CatalogItem

describe('historial de muebles', () => {
  beforeEach(() => useStudio.getState().setScene(null))

  it('agregar, mover, deshacer y rehacer', () => {
    addPlacement(sofa, 0, -3)
    const uid = useStudio.getState().selectedUid!
    updatePlacement(uid, { x: 1 })
    expect(useStudio.getState().placements[0].x).toBe(1)
    useStudio.getState().undo()
    expect(useStudio.getState().placements[0].x).toBe(0)
    useStudio.getState().undo()
    expect(useStudio.getState().placements).toHaveLength(0)
    useStudio.getState().redo()
    useStudio.getState().redo()
    expect(useStudio.getState().placements[0].x).toBe(1)
  })

  it('duplicar y borrar', () => {
    addPlacement(sofa, 0, -3)
    duplicatePlacement(useStudio.getState().selectedUid!)
    expect(useStudio.getState().placements).toHaveLength(2)
    removePlacement(useStudio.getState().selectedUid!)
    expect(useStudio.getState().placements).toHaveLength(1)
    expect(useStudio.getState().selectedUid).toBeNull()
  })

  it('el arrastre queda como un solo paso del historial', () => {
    addPlacement(sofa, 0, -3)
    const before = useStudio.getState().placements
    const s = useStudio.getState()
    s.preview([{ ...before[0], x: 0.5 }])
    s.preview([{ ...before[0], x: 1.0 }])
    s.commitFrom(before)
    useStudio.getState().undo()
    expect(useStudio.getState().placements[0].x).toBe(0)
  })

  it('máximo 30 pasos', () => {
    addPlacement(sofa, 0, -3)
    const uid = useStudio.getState().selectedUid!
    for (let i = 0; i < 40; i++) updatePlacement(uid, { x: i })
    expect(useStudio.getState().past.length).toBe(30)
  })
})

describe('calibración de escala', () => {
  it('scale_k = escena / real', () => {
    expect(scaleFromCalibration([[0, 0], [3, 0]], 330)).toBeCloseTo(3 / 3.3)
    expect(scaleFromCalibration([[0, 0], [0, -2]], 200)).toBeCloseTo(1)
  })
  it('rechaza valores absurdos', () => {
    expect(scaleFromCalibration([[0, 0]], 100)).toBeNull()
    expect(scaleFromCalibration([[0, 0], [3, 0]], 0)).toBeNull()
    expect(scaleFromCalibration([[0, 0], [3, 0]], 10)).toBeNull()
  })
})

describe('sugerencias (fantasmas)', () => {
  beforeEach(() => useStudio.getState().setScene(null))
  it('aceptar todas reemplaza los muebles que se reacomodaban', () => {
    addPlacement(sofa, 0, -3)
    const old = useStudio.getState().placements[0]
    const ghost = { ...old, uid: 'g1', x: 1, z: -4, source: 'heuristic' as const }
    useStudio.getState().setGhosts({ placements: [ghost], notes: [], replaceUids: [old.uid] })
    acceptGhosts()
    const ps = useStudio.getState().placements
    expect(ps).toHaveLength(1)
    expect(ps[0].uid).toBe('g1')
    expect(useStudio.getState().ghosts).toBeNull()
    useStudio.getState().undo()
    expect(useStudio.getState().placements[0].uid).toBe(old.uid)
  })
  it('aceptar todas quita los muebles que no encontraron lugar', () => {
    addPlacement(sofa, 0, -3)
    addPlacement(sofa, 1, -3)
    const [a, b] = useStudio.getState().placements
    const ghost = { ...a, uid: 'g1', x: 2, source: 'heuristic' as const }
    useStudio.getState().setGhosts({ placements: [ghost], notes: [], replaceUids: [a.uid, b.uid] })
    acceptGhosts()
    expect(useStudio.getState().placements.map((p) => p.uid)).toEqual(['g1'])
  })

  it('aceptar una deja las demás pendientes', () => {
    const g = (uid: string) => ({ uid, item_id: 'sofa', mode: 'cutout' as const, x: 0, z: -3, yaw_deg: 0, source: 'heuristic' as const })
    useStudio.getState().setGhosts({ placements: [g('a'), g('b')], notes: [], replaceUids: [] })
    acceptGhosts('a')
    expect(useStudio.getState().placements.map((p) => p.uid)).toEqual(['a'])
    expect(useStudio.getState().ghosts!.placements.map((p) => p.uid)).toEqual(['b'])
  })
})
