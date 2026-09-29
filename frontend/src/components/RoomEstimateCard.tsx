import type { Scene } from '../api/client'
import { useStudio } from '../store/useStudio'

const WARNING_TEXT: Record<string, string> = {
  piso_no_encontrado: 'No se encontró el piso en la foto.',
  escala_dudosa: 'La escala puede estar mal (altura de cámara rara). Usa "Calibrar medida".',
  poco_piso_visible: 'Se ve poco piso: las medidas son menos confiables.',
  piso_manual: 'Piso definido a mano: sin oclusión ni medidas del espacio. Usa "Calibrar medida" si conoces una medida.',
}

export default function RoomEstimateCard({ scene }: { scene: Scene }) {
  // Tras calibrar, las medidas del espacio se dividen por scale_k (PLAN 1.7)
  const k = useStudio((s) => s.scaleK)
  const raw = scene.room_estimate
  const r = raw && {
    ...raw,
    visible_floor_area_m2: raw.visible_floor_area_m2 == null ? null : raw.visible_floor_area_m2 / (k * k),
    floor_extent_m: raw.floor_extent_m && {
      width: raw.floor_extent_m.width / k,
      depth: raw.floor_extent_m.depth / k,
    },
    ceiling_height_m: raw.ceiling_height_m == null ? null : raw.ceiling_height_m / k,
  }
  const fmt = (v: number | null | undefined, unit: string) => (v == null ? '—' : `${v.toFixed(1)} ${unit}`)
  return (
    <section data-testid="room-card" className="rounded-lg border border-stone-200 bg-white p-3 text-sm">
      <h3 className="mb-1 font-semibold">Medidas estimadas del espacio</h3>
      {r ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
          <dt className="text-stone-500">Área visible</dt>
          <dd>{fmt(r.visible_floor_area_m2, 'm²')}</dd>
          <dt className="text-stone-500">Ancho × fondo</dt>
          <dd>{r.floor_extent_m ? `${r.floor_extent_m.width.toFixed(1)} × ${r.floor_extent_m.depth.toFixed(1)} m` : '—'}</dd>
          <dt className="text-stone-500">Altura de techo</dt>
          <dd>{r.ceiling_height_m ? `${r.ceiling_height_m.toFixed(2)} m` : 'no se ve el techo'}</dd>
          <dt className="text-stone-500">Confianza</dt>
          <dd className="capitalize">{k !== 1 ? 'calibrada' : r.confidence}</dd>
        </dl>
      ) : (
        <p className="text-stone-500">Sin datos.</p>
      )}
      <p className="mt-2 text-xs text-stone-500">
        Estimadas desde la foto (solo lo visible); pueden variar ±15 %. Usa "Calibrar medida" si conoces una medida real.
      </p>
      {scene.warnings.map((w) => (
        <p key={w} className="mt-1 rounded bg-amber-50 p-1.5 text-xs text-amber-800">
          {WARNING_TEXT[w] ?? w}
        </p>
      ))}
    </section>
  )
}
