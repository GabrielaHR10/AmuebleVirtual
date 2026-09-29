export interface Health {
  ok: boolean
  device: string
  version: string
}

export type Category =
  | 'sofa'
  | 'armchair'
  | 'chair'
  | 'bed'
  | 'nightstand'
  | 'dining_table'
  | 'coffee_table'
  | 'desk'
  | 'tv_stand'
  | 'shelf'
  | 'wardrobe'
  | 'rug'
  | 'lamp'
  | 'plant'
  | 'other'

export interface Dimensions {
  width: number
  depth: number
  height: number
}

export interface CatalogItem {
  id: string
  name: string
  category: Category
  dimensions_cm: Dimensions
  extra_dimensions_cm: Record<string, number>
  dimensions_source: string
  dimensions_verified: boolean
  preferred_mode: 'cutout' | '3d'
  glb_url: string | null
  cutout_url: string | null
  photo_url: string | null
  thumb_url: string | null
  yaw_offset_deg: number
  against_wall: boolean
  source: string
  license: string
  notes: string[]
  user_created: boolean
  cutout_ratio: number | null
  photo_warning: string | null
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `El servidor respondió ${res.status}`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // respuesta sin JSON: se deja el mensaje genérico
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  return parse<Health>(await fetch('/api/health', { signal }))
}

export function describeHealth(h: Health): string {
  return `Servidor conectado · ${h.device.toUpperCase()} · v${h.version}`
}

export async function getCatalog(): Promise<CatalogItem[]> {
  return parse<CatalogItem[]>(await fetch('/api/catalog'))
}

export async function createCatalogItem(form: FormData): Promise<CatalogItem> {
  return parse<CatalogItem>(await fetch('/api/catalog', { method: 'POST', body: form }))
}

export async function deleteCatalogItem(id: string): Promise<void> {
  await parse<{ ok: boolean }>(await fetch(`/api/catalog/${encodeURIComponent(id)}`, { method: 'DELETE' }))
}

// ---------- Escenas (PLAN §5.1) ----------

export interface RoomEstimate {
  visible_floor_area_m2: number | null
  floor_extent_m: { width: number; depth: number } | null
  ceiling_height_m: number | null
  confidence: 'alta' | 'media' | 'baja'
  method: string
}

export interface Placement {
  uid: string
  item_id: string
  mode: '3d' | 'cutout'
  x: number
  z: number
  yaw_deg: number
  source: 'manual' | 'heuristic' | 'vlm'
}

export interface Scene {
  id: string
  kind: 'photo'
  image: { url: string; width: number; height: number }
  camera: { fov_y_deg: number; intrinsics_norm: number[][]; matrix_world: number[] }
  floor: { found: boolean; normal: number[] | null; d: number | null; inlier_ratio: number; frame: number[] | null }
  camera_height_m: number | null
  scale_k: number
  room_estimate: RoomEstimate | null
  warnings: string[]
  assets: Record<string, string>
  placements: Placement[]
  model: string
  timings_ms: Record<string, number>
  created_at: string | null
}

export async function uploadScene(file: File): Promise<Scene> {
  const form = new FormData()
  form.append('file', file)
  return parse<Scene>(await fetch('/api/scenes', { method: 'POST', body: form }))
}

export async function getScenes(): Promise<Scene[]> {
  return parse<Scene[]>(await fetch('/api/scenes'))
}

export async function getScene(id: string): Promise<Scene> {
  return parse<Scene>(await fetch(`/api/scenes/${encodeURIComponent(id)}`))
}

export async function savePlacements(id: string, placements: Placement[], scaleK: number): Promise<Scene> {
  return parse<Scene>(
    await fetch(`/api/scenes/${encodeURIComponent(id)}/placements`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ placements, scale_k: scaleK }),
    }),
  )
}

export async function saveManualFloor(id: string, normal: number[], d: number): Promise<Scene> {
  return parse<Scene>(
    await fetch(`/api/scenes/${encodeURIComponent(id)}/floor`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ normal, d }),
    }),
  )
}

export interface SuggestResponse {
  placements: Placement[]
  notes: string[]
}

export async function suggestPlacements(
  id: string,
  itemIds: string[],
  useVlm: boolean,
  replaceUids: string[],
): Promise<SuggestResponse> {
  return parse<SuggestResponse>(
    await fetch(`/api/scenes/${encodeURIComponent(id)}/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_ids: itemIds, use_vlm: useVlm, replace_uids: replaceUids }),
    }),
  )
}

export async function getVlmStatus(): Promise<{ available: boolean; model: string; reason: string | null }> {
  return parse(await fetch('/api/scenes/vlm/status'))
}

export interface ExtractedDimensions {
  raw_table: Record<string, string>
  width_cm: number
  depth_cm: number
  height_cm: number
  extra_dimensions_cm: Record<string, number>
  units_detected: string | null
}

export async function extractDimensions(table: File): Promise<ExtractedDimensions> {
  const form = new FormData()
  form.append('table_image', table)
  return parse<ExtractedDimensions>(await fetch('/api/catalog/extract-dimensions', { method: 'POST', body: form }))
}
