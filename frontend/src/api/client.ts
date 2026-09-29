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
