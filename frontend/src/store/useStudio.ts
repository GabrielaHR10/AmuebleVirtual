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
  /** Calibración de escala (PLAN 2.8): puntos del piso (x, z) marcados por el usuario. */
  calibration: { active: boolean; points: [number, number][] }
  setCalibration: (c: { active: boolean; points: [number, number][] }) => void
  /** Piso manual (PLAN 2.9): puntos 3D (coords de cámara) marcados sobre la foto. */
  manualFloor: { active: boolean; points: [number, number, number][] }
  setManualFloor: (m: { active: boolean; points: [number, number, number][] }) => void
  /** Sugerencias pendientes (PLAN 3.4): se ven como fantasmas hasta aceptarlas. */
  ghosts: { placements: Placement[]; notes: string[]; replaceUids: string[] } | null
  setGhosts: (g: { placements: Placement[]; notes: string[]; replaceUids: string[] } | null) => void
  /** Ajustes de vista (PLAN 2.11). */
  shadowOpacity: number
  exposure: number
  setView: (v: { shadowOpacity?: number; exposure?: number }) => void
  /** Avisos flotantes (errores del servidor en español). */
  toasts: { id: number; text: string }[]
  pushToast: (text: string) => void
  dismissToast: (id: number) => void
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
      calibration: { active: false, points: [] },
      manualFloor: { active: false, points: [] },
      ghosts: null,
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
  calibration: { active: false, points: [] },
  setCalibration: (calibration) => set({ calibration }),
  manualFloor: { active: false, points: [] },
  setManualFloor: (manualFloor) => set({ manualFloor }),
  ghosts: null,
  setGhosts: (ghosts) => set({ ghosts }),
  shadowOpacity: 0.3,
  exposure: 1,
  setView: (v) => set(v),
  toasts: [],
  pushToast: (text) => {
    const id = Date.now() + Math.random()
    set((s) => ({ toasts: [...s.toasts.filter((t) => t.text !== text), { id, text }] }))
    setTimeout(() => useStudio.getState().dismissToast(id), 6000)
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
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

/** scale_k = distancia en la escena / distancia real (PLAN 2.8). */
export function scaleFromCalibration(points: [number, number][], realCm: number): number | null {
  if (points.length !== 2 || !(realCm > 0)) return null
  const [[x1, z1], [x2, z2]] = points
  const scene = Math.hypot(x2 - x1, z2 - z1)
  const k = scene / (realCm / 100)
  return k > 0.2 && k < 5 ? k : null
}

/** Aceptar sugerencias: todas o solo una (por uid). Reemplaza los muebles que se estaban reacomodando. */
export function acceptGhosts(uid?: string) {
  const { ghosts, placements, commit, setGhosts } = useStudio.getState()
  if (!ghosts) return
  const accepted = uid ? ghosts.placements.filter((g) => g.uid === uid) : ghosts.placements
  const acceptedItems = accepted.map((g) => g.item_id)
  // al reacomodar, el fantasma reemplaza al mueble puesto del mismo tipo que se estaba moviendo
  const toRemove = new Set<string>()
  for (const itemId of acceptedItems) {
    const old = placements.find((p) => ghosts.replaceUids.includes(p.uid) && p.item_id === itemId && !toRemove.has(p.uid))
    if (old) toRemove.add(old.uid)
  }
  commit([...placements.filter((p) => !toRemove.has(p.uid)), ...accepted])
  const rest = ghosts.placements.filter((g) => !accepted.includes(g))
  setGhosts(rest.length ? { ...ghosts, placements: rest, replaceUids: ghosts.replaceUids.filter((u) => !toRemove.has(u)) } : null)
}
