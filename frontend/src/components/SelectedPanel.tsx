import { CATEGORY_LABELS, formatDims } from '../catalog'
import { duplicatePlacement, removePlacement, updatePlacement, useStudio } from '../store/useStudio'
import { useFits } from '../three/useFits'

export default function SelectedPanel() {
  const { placements, catalog, selectedUid, modelWarnings } = useStudio()
  const fits = useFits()
  const p = placements.find((x) => x.uid === selectedUid)
  const item = p && catalog.find((i) => i.id === p.item_id)
  if (!p || !item) {
    return (
      <section className="rounded-lg border border-stone-200 bg-white p-3 text-sm text-stone-500">
        Haz clic en un mueble del catálogo para agregarlo. Arrástralo para moverlo; <b>Q/E</b> gira,
        <b> Supr</b> borra, <b>Ctrl/Cmd+D</b> duplica, <b>Ctrl/Cmd+Z</b> deshace.
      </section>
    )
  }
  const fit = fits[p.uid]
  const warning = p.mode === '3d' ? modelWarnings[item.id] : item.photo_warning
  const hasBoth = !!item.glb_url && !!item.cutout_url
  const yaw = ((Math.round(p.yaw_deg) % 360) + 360) % 360

  return (
    <section data-testid="selected-panel" className="space-y-2 rounded-lg border border-stone-200 bg-white p-3 text-sm">
      <div>
        <h3 className="font-semibold leading-tight">{item.name}</h3>
        <p className="text-stone-600">{formatDims(item.dimensions_cm)}</p>
        <p className="text-xs text-stone-500">{CATEGORY_LABELS[item.category]}</p>
      </div>
      {fit && (
        <p className={`rounded p-1.5 text-xs ${fit.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'}`}>
          {fit.ok ? 'Cabe aquí' : fit.message}
        </p>
      )}
      {!item.dimensions_verified && <p className="text-xs text-amber-700">Medidas sin verificar</p>}
      {warning && <p className="rounded bg-orange-50 p-1.5 text-xs text-orange-800">{warning}</p>}
      <label className="block">
        Rotación: {yaw}°
        <input
          type="range"
          min={0}
          max={359}
          value={yaw}
          onChange={(e) => updatePlacement(p.uid, { yaw_deg: Number(e.target.value) })}
          className="w-full"
        />
      </label>
      {hasBoth && (
        <div className="flex gap-1 text-xs">
          {(['3d', 'cutout'] as const).map((m) => (
            <button
              key={m}
              onClick={() => updatePlacement(p.uid, { mode: m })}
              className={`rounded px-2 py-1 ${p.mode === m ? 'bg-stone-800 text-white' : 'bg-stone-100'}`}
            >
              {m === '3d' ? 'Modelo 3D' : 'Recorte de foto'}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2 pt-1">
        <button onClick={() => duplicatePlacement(p.uid)} className="rounded bg-stone-100 px-2 py-1">
          Duplicar
        </button>
        <button onClick={() => removePlacement(p.uid)} className="rounded bg-red-50 px-2 py-1 text-red-700">
          Borrar
        </button>
      </div>
    </section>
  )
}
