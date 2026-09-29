import { beforeEach, describe, expect, it } from 'vitest'
import type { CatalogItem } from '../api/client'
import { addPlacement, duplicatePlacement, removePlacement, updatePlacement, useStudio } from './useStudio'

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
