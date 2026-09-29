import { useMemo, useState } from 'react'
import { Matrix4 } from 'three'
import type { CatalogItem, Category } from '../api/client'
import { CATEGORY_LABELS, formatDims, thumbOf } from '../catalog'
import { addPlacement, useStudio } from '../store/useStudio'
import { findFreeSpot } from '../three/fit'
import { dropPoint } from '../three/math'
import { getLoadedMask } from '../three/useFits'

/**
 * Clic en un mueble → se agrega en el piso bajo el centro de la imagen (PLAN 2.7); si ahí no cabe
 * o se cruza con otro, en el lugar libre más cercano.
 */
function addToScene(item: CatalogItem) {
  const { scene, placements, catalog, scaleK } = useStudio.getState()
  if (!scene?.floor.frame) return
  const frame = new Matrix4().fromArray(scene.floor.frame)
  const cameraWorld = new Matrix4().fromArray(scene.camera.matrix_world)
  const p = dropPoint(frame, cameraWorld)
  const byId = new Map(catalog.map((i) => [i.id, i]))
  const others = placements.flatMap((o) => (byId.has(o.item_id) ? [{ p: o, item: byId.get(o.item_id)! }] : []))
  const mask = scene.warnings.includes('piso_manual') ? null : getLoadedMask(scene.assets.floor_mask_png)
  const [x, z] = findFreeSpot(p.x, p.z, item, others, {
    mask, frame, cameraWorld, intrinsics: scene.camera.intrinsics_norm, scaleK,
  })
  addPlacement(item, x, z)
}

export default function CatalogPanel() {
  const catalog = useStudio((s) => s.catalog)
  const canAdd = useStudio((s) => !!s.scene?.floor.frame)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<Category | ''>('')

  const categories = useMemo(() => [...new Set(catalog.map((i) => i.category))], [catalog])
  const shown = catalog.filter(
    (i) =>
      (!category || i.category === category) &&
      (!query || i.name.toLowerCase().includes(query.toLowerCase())),
  )

  return (
    <aside className="flex w-64 flex-col border-r border-stone-200 bg-stone-50">
      <div className="space-y-2 border-b border-stone-200 p-3">
        <h2 className="text-sm font-semibold">Catálogo</h2>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar…"
          className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Category | '')}
          className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
        {!canAdd && <p className="text-xs text-amber-700">Sin piso detectado: no se pueden agregar muebles.</p>}
      </div>
      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
        {shown.map((item) => {
          const thumb = thumbOf(item)
          return (
            <li key={item.id}>
              <button
                data-testid="catalog-add"
                disabled={!canAdd}
                onClick={() => addToScene(item)}
                className="flex w-full items-center gap-2 rounded p-1.5 text-left hover:bg-white disabled:opacity-50"
              >
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-white">
                  {thumb && <img src={thumb} alt="" className="max-h-full max-w-full object-contain" />}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm">{item.name}</span>
                  <span className="block text-xs text-stone-500">{formatDims(item.dimensions_cm)}</span>
                  {!item.dimensions_verified && (
                    <span className="block text-[11px] text-amber-700">Medidas sin verificar</span>
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="border-t border-stone-200 p-2 text-[11px] text-stone-500">Modelos 3D: Poly Haven (CC0)</p>
    </aside>
  )
}
