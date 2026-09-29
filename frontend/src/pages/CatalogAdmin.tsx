import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { createCatalogItem, deleteCatalogItem, getCatalog, type CatalogItem, type Category } from '../api/client'
import { CATEGORY_LABELS, formatDims, thumbOf } from '../catalog'

function ItemCard({ item, onDelete }: { item: CatalogItem; onDelete: (id: string) => void }) {
  const [confirming, setConfirming] = useState(false)
  const thumb = thumbOf(item)
  return (
    <li data-testid="catalog-card" className="flex flex-col rounded-lg border border-stone-200 bg-white p-3">
      <div className="flex h-36 items-center justify-center rounded bg-stone-100">
        {thumb ? <img src={thumb} alt={item.name} className="max-h-full max-w-full object-contain" /> : null}
      </div>
      <h3 className="mt-2 text-sm font-medium leading-tight">{item.name}</h3>
      <p className="text-sm text-stone-700">{formatDims(item.dimensions_cm)}</p>
      <p className="text-xs text-stone-500">
        {CATEGORY_LABELS[item.category]} · {item.preferred_mode === '3d' ? 'Modelo 3D' : 'Recorte de foto'}
      </p>
      <div className="mt-1 flex flex-wrap gap-1">
        {!item.dimensions_verified && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">Medidas sin verificar</span>
        )}
        {item.photo_warning && (
          <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-800">{item.photo_warning}</span>
        )}
      </div>
      {item.user_created && (
        <div className="mt-auto pt-2 text-xs">
          {confirming ? (
            <span className="flex gap-2">
              ¿Borrar?
              <button className="text-red-700 underline" onClick={() => onDelete(item.id)}>
                Sí
              </button>
              <button className="underline" onClick={() => setConfirming(false)}>
                No
              </button>
            </span>
          ) : (
            <button className="text-stone-500 underline" onClick={() => setConfirming(true)}>
              Borrar
            </button>
          )}
        </div>
      )}
    </li>
  )
}

function NewItemForm({ onCreated }: { onCreated: (item: CatalogItem) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const table = data.get('table_image')
    if (table instanceof File && table.size === 0) data.delete('table_image')
    setBusy(true)
    setError(null)
    try {
      onCreated(await createCatalogItem(data))
      form.reset()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const input = 'mt-1 w-full rounded border border-stone-300 px-2 py-1.5 text-sm'
  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
      <h2 className="font-semibold">Agregar mueble</h2>
      <p className="text-xs text-stone-500">
        Toma la foto de frente, a la altura del centro del mueble, con fondo despejado y buena luz.
      </p>
      <label className="block text-sm">
        Foto del mueble
        <input name="photo" type="file" accept="image/jpeg,image/png" required className={input} />
      </label>
      <label className="block text-sm">
        Foto de la tabla de medidas (opcional)
        <input name="table_image" type="file" accept="image/jpeg,image/png" className={input} />
      </label>
      <label className="block text-sm">
        Nombre
        <input name="name" required placeholder="Sofá gris tres puestos" className={input} />
      </label>
      <label className="block text-sm">
        Categoría
        <select name="category" required className={input} defaultValue="sofa">
          {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
      </label>
      <div className="grid grid-cols-3 items-end gap-2">
        {[
          ['width_cm', 'Ancho (frente)'],
          ['depth_cm', 'Fondo'],
          ['height_cm', 'Alto'],
        ].map(([name, label]) => (
          <label key={name} className="block text-sm">
            {label}
            <input name={name} type="number" min="1" step="0.1" required placeholder="cm" className={input} />
          </label>
        ))}
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full rounded bg-stone-800 py-2 text-sm font-medium text-white disabled:opacity-60"
      >
        {busy ? 'Quitando el fondo a la foto… (~10 s)' : 'Guardar mueble'}
      </button>
    </form>
  )
}

export default function CatalogAdmin() {
  const [items, setItems] = useState<CatalogItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    getCatalog()
      .then(setItems)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])
  useEffect(load, [load])

  async function remove(id: string) {
    try {
      await deleteCatalogItem(id)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6 p-6 md:grid-cols-[320px_1fr]">
      <NewItemForm onCreated={load} />
      <section>
        <h2 className="mb-3 font-semibold">Catálogo {items ? `(${items.length})` : ''}</h2>
        {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        {items === null ? (
          <p className="text-sm text-stone-500">Cargando…</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} onDelete={remove} />
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-stone-500">Modelos 3D: Poly Haven (CC0).</p>
      </section>
    </div>
  )
}
