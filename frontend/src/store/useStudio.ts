import { create } from 'zustand'
import type { CatalogItem, Scene } from '../api/client'

export interface Toggles {
  occlusion: boolean
  floorMask: boolean
  grid: boolean
  shadows: boolean
}

interface StudioState {
  scene: Scene | null
  catalog: CatalogItem[]
  toggles: Toggles
  setScene: (scene: Scene | null) => void
  setCatalog: (items: CatalogItem[]) => void
  toggle: (key: keyof Toggles) => void
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

export const useStudio = create<StudioState>((set) => ({
  scene: null,
  catalog: [],
  toggles: { occlusion: true, floorMask: false, grid: gridDefault(), shadows: true },
  setScene: (scene) => set({ scene }),
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
}))
