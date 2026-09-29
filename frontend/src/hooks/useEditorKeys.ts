import { useEffect } from 'react'
import { duplicatePlacement, removePlacement, updatePlacement, useStudio } from '../store/useStudio'

/** Atajos del editor: Q/E giran ±15°, Supr/Backspace borra, Ctrl/Cmd+D duplica, Ctrl/Cmd+Z deshace (PLAN 2.7). */
export function useEditorKeys(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) {
        return
      }
      const { selectedUid, placements, undo, redo } = useStudio.getState()
      const mod = e.metaKey || e.ctrlKey
      const key = e.key.toLowerCase()
      if (mod && key === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
        return
      }
      if (mod && key === 'y') {
        e.preventDefault()
        redo()
        return
      }
      if (!selectedUid) return
      const p = placements.find((x) => x.uid === selectedUid)
      if (!p) return
      if (mod && key === 'd') {
        e.preventDefault()
        duplicatePlacement(selectedUid)
      } else if (!mod && (key === 'q' || key === 'e')) {
        updatePlacement(selectedUid, { yaw_deg: (p.yaw_deg + (key === 'q' ? 15 : -15) + 360) % 360 })
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        removePlacement(selectedUid)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [enabled])
}
