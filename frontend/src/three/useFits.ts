import { useEffect, useMemo, useState } from 'react'
import { Matrix4 } from 'three'
import type { CatalogItem } from '../api/client'
import { useStudio } from '../store/useStudio'
import { fitStatus, type FitResult, type MaskData } from './fit'

const maskCache = new Map<string, Promise<MaskData>>()

function loadMask(url: string): Promise<MaskData> {
  let p = maskCache.get(url)
  if (!p) {
    p = new Promise<MaskData>((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        const c = document.createElement('canvas')
        c.width = img.naturalWidth
        c.height = img.naturalHeight
        const g = c.getContext('2d', { willReadFrequently: true })!
        g.drawImage(img, 0, 0)
        resolve({ width: c.width, height: c.height, data: g.getImageData(0, 0, c.width, c.height).data })
      }
      img.onerror = () => reject(new Error('No se pudo cargar la máscara del piso'))
      img.src = url
    })
    maskCache.set(url, p)
  }
  return p
}

export function useFloorMask(url: string | undefined): MaskData | null {
  const [mask, setMask] = useState<{ url: string; data: MaskData } | null>(null)
  useEffect(() => {
    if (!url) return
    let alive = true
    loadMask(url)
      .then((data) => alive && setMask({ url, data }))
      .catch(() => undefined)
    return () => {
      alive = false
    }
  }, [url])
  return mask && mask.url === url ? mask.data : null
}

/** ¿Cabe cada mueble ubicado? (por uid) */
export function useFits(): Record<string, FitResult> {
  const { scene, placements, catalog, scaleK } = useStudio()
  const mask = useFloorMask(scene?.assets.floor_mask_png)
  return useMemo(() => {
    const out: Record<string, FitResult> = {}
    if (!scene?.floor.frame) return out
    const byId = new Map(catalog.map((i) => [i.id, i]))
    const withItems = placements
      .map((p) => ({ p, item: byId.get(p.item_id) }))
      .filter((x): x is { p: (typeof placements)[number]; item: CatalogItem } => !!x.item)
    const ctx = {
      mask,
      frame: new Matrix4().fromArray(scene.floor.frame),
      cameraWorld: new Matrix4().fromArray(scene.camera.matrix_world),
      intrinsics: scene.camera.intrinsics_norm,
      scaleK,
    }
    for (const { p, item } of withItems) out[p.uid] = fitStatus(p, item, withItems, ctx)
    return out
  }, [scene, placements, catalog, scaleK, mask])
}
