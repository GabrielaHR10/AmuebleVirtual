import { create } from 'zustand'
import type { CatalogItem, Placement, Scene } from '../api/client'

export interface Toggles {
  occlusion: boolean
  floorMask: boolean
  grid: boolean
  shadows: boolean
}

const HISTORY_LIMIT = 30

interface StudioState {
  scene: Scene | null
  catalog: CatalogItem[]
  toggles: Toggles
  placements: Placement[]
  scaleK: number
  selectedUid: string | null
  past: Placement[][]
  future: Placement[][]
  setScene: (scene: Scene | null) => void
  setCatalog: (items: CatalogItem[]) => void
  toggle: (key: keyof Toggles) => void
  select: (uid: string | null) => void
  /** Cambia los muebles guardando el estado anterior en el historial. */
  commit: (next: Placement[]) => void
  /** Cambia sin historial (durante el arrastre); al soltar se llama `commitFrom`. */
  preview: (next: Placement[]) => void
  commitFrom: (before: Placement[]) => void
  undo: () => void
  redo: () => void
  setScaleK: (k: number) => void
  /** Avisos de los modelos 3D (alto del GLB ≠ ficha), por item_id. */
  modelWarnings: Record<string, string | null>
  setModelWarning: (itemId: string, warning: string | null) => void
}

const GRID_SEEN_KEY = 'estudio.gridSeen'

function gridDefault(): boolean {
  // La cuadrícula viene encendida la primera vez (PLAN 2.6)
  try {
    return localStorage.getItem(GRID_SEEN_KEY) !== '1'
  } catch {
    return true
  }
}

let counter = 0
export function newUid(): string {
  counter += 1
  return `p_${Date.now().toString(36)}_${counter}`
}

const pushPast = (past: Placement[][], p: Placement[]) => [...past, p].slice(-HISTORY_LIMIT)

export const useStudio = create<StudioState>((set) => ({
  scene: null,
  catalog: [],
  toggles: { occlusion: true, floorMask: false, grid: gridDefault(), shadows: true },
  placements: [],
  scaleK: 1,
  selectedUid: null,
  past: [],
  future: [],
  setScene: (scene) =>
    set({
      scene,
      placements: scene?.placements ?? [],
      scaleK: scene?.scale_k ?? 1,
      selectedUid: null,
      past: [],
      future: [],
    }),
  setCatalog: (catalog) => set({ catalog }),
  toggle: (key) =>
    set((s) => {
      if (key === 'grid') {
        try {
          localStorage.setItem(GRID_SEEN_KEY, '1')
        } catch {
          // sin almacenamiento: no pasa nada
        }
      }
      return { toggles: { ...s.toggles, [key]: !s.toggles[key] } }
    }),
  select: (selectedUid) => set({ selectedUid }),
  commit: (next) => set((s) => ({ placements: next, past: pushPast(s.past, s.placements), future: [] })),
  preview: (next) => set({ placements: next }),
  commitFrom: (before) =>
    set((s) => (before === s.placements ? {} : { past: pushPast(s.past, before), future: [] })),
  undo: () =>
    set((s) => {
      if (!s.past.length) return {}
      const prev = s.past[s.past.length - 1]
      return { placements: prev, past: s.past.slice(0, -1), future: [s.placements, ...s.future] }
    }),
  redo: () =>
    set((s) => {
      if (!s.future.length) return {}
      const [next, ...rest] = s.future
      return { placements: next, past: pushPast(s.past, s.placements), future: rest }
    }),
  setScaleK: (scaleK) => set({ scaleK }),
  modelWarnings: {},
  setModelWarning: (itemId, warning) =>
    set((s) => (s.modelWarnings[itemId] === warning ? {} : { modelWarnings: { ...s.modelWarnings, [itemId]: warning } })),
}))

// ---------- Acciones de alto nivel ----------

export function addPlacement(item: CatalogItem, x: number, z: number) {
  const { placements, commit } = useStudio.getState()
  const p: Placement = {
    uid: newUid(),
    item_id: item.id,
    mode: item.preferred_mode === '3d' && item.glb_url ? '3d' : 'cutout',
    x,
    z,
    yaw_deg: 0,
    source: 'manual',
  }
  commit([...placements, p])
  useStudio.getState().select(p.uid)
}

export function updatePlacement(uid: string, patch: Partial<Placement>) {
  const { placements, commit } = useStudio.getState()
  commit(placements.map((p) => (p.uid === uid ? { ...p, ...patch } : p)))
}

export function removePlacement(uid: string) {
  const { placements, commit, select } = useStudio.getState()
  commit(placements.filter((p) => p.uid !== uid))
  select(null)
}

export function duplicatePlacement(uid: string) {
  const { placements, commit, select } = useStudio.getState()
  const src = placements.find((p) => p.uid === uid)
  if (!src) return
  const copy = { ...src, uid: newUid(), x: src.x + 0.3, z: src.z + 0.3, source: 'manual' as const }
  commit([...placements, copy])
  select(copy.uid)
}
