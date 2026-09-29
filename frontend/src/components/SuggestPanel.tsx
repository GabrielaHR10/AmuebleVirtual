import { useEffect, useState } from 'react'
import { getVlmStatus, savePlacements, suggestPlacements } from '../api/client'
import { acceptGhosts, useStudio } from '../store/useStudio'

/** "Sugerir ubicación" (PLAN 3.4): reacomoda los muebles puestos y/o agrega los elegidos. */
export default function SuggestPanel() {
  const { scene, placements, catalog, ghosts, setGhosts, pushToast } = useStudio()
  const [extra, setExtra] = useState<string[]>([])
  const [useVlm, setUseVlm] = useState(false)
  const [vlm, setVlm] = useState<{ available: boolean; reason: string | null }>({ available: false, reason: null })
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getVlmStatus()
      .then((s) => setVlm({ available: s.available, reason: s.reason }))
      .catch(() => setVlm({ available: false, reason: 'No se pudo consultar la IA local' }))
  }, [])

  if (!scene?.floor.frame) return null
  const names = new Map(catalog.map((i) => [i.id, i.name]))

  async function run() {
    if (!scene) return
    const itemIds = [...placements.map((p) => p.item_id), ...extra]
    if (!itemIds.length) {
      pushToast('Agrega muebles o elige algunos para sugerir su ubicación.')
      return
    }
    setBusy(true)
    try {
      // guardar primero, para que el servidor conozca los muebles actuales
      await savePlacements(scene.id, placements, useStudio.getState().scaleK)
      const res = await suggestPlacements(scene.id, itemIds, useVlm, placements.map((p) => p.uid))
      setGhosts({ placements: res.placements, notes: res.notes, replaceUids: placements.map((p) => p.uid) })
      setExtra([])
    } catch (e) {
      pushToast(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section data-testid="suggest-panel" className="space-y-2 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm">
      <h3 className="font-semibold">Sugerir ubicación</h3>
      {!ghosts ? (
        <>
          <p className="text-xs text-stone-600">
            Reacomoda los muebles puestos{extra.length ? ' y agrega los elegidos' : ''}.
          </p>
          <select
            value=""
            onChange={(e) => e.target.value && setExtra([...extra, e.target.value])}
            className="w-full rounded border border-stone-300 px-2 py-1 text-xs"
          >
            <option value="">+ Agregar un mueble a la sugerencia…</option>
            {catalog.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
          {extra.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {extra.map((id, k) => (
                <button key={k} onClick={() => setExtra(extra.filter((_, j) => j !== k))} className="rounded bg-white px-1.5 py-0.5 text-xs">
                  {names.get(id)} ×
                </button>
              ))}
            </div>
          )}
          <label
            className={`flex items-center gap-2 text-xs ${vlm.available ? '' : 'opacity-50'}`}
            title={vlm.available ? 'La IA local elige entre las opciones válidas (tarda ~1 min)' : vlm.reason ?? ''}
          >
            <input type="checkbox" disabled={!vlm.available} checked={useVlm} onChange={() => setUseVlm(!useVlm)} />
            Usar IA local (Ollama)
          </label>
          <button onClick={run} disabled={busy} className="w-full rounded bg-sky-700 py-1.5 font-medium text-white disabled:opacity-60">
            {busy ? (useVlm ? 'La IA local está pensando… (~1 min)' : 'Buscando lugares…') : 'Sugerir ubicación'}
          </button>
        </>
      ) : (
        <>
          <ul className="space-y-1 text-xs">
            {ghosts.notes.map((n, k) => (
              <li key={k} className="text-stone-700">
                • {n}
              </li>
            ))}
          </ul>
          <ul className="space-y-1">
            {ghosts.placements.map((g) => (
              <li key={g.uid} data-testid="ghost-item" className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate">{names.get(g.item_id)}</span>
                <button onClick={() => acceptGhosts(g.uid)} className="rounded bg-white px-2 py-0.5">
                  Aceptar
                </button>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button onClick={() => acceptGhosts()} className="rounded bg-sky-700 px-2 py-1 text-white">
              Aceptar todas
            </button>
            <button onClick={() => setGhosts(null)} className="rounded bg-white px-2 py-1">
              Descartar
            </button>
          </div>
        </>
      )}
    </section>
  )
}
