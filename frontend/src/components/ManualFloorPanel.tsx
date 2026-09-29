import { useState } from 'react'
import { Matrix4, Vector3 } from 'three'
import { saveManualFloor } from '../api/client'
import { useStudio } from '../store/useStudio'
import { floorFrameFromPlane, planeFromPoints } from '../three/math'

/** "Definir piso" (PLAN 2.9): si no se detectó el piso, 3 clics sobre el piso de la foto. */
export default function ManualFloorPanel() {
  const { scene, manualFloor, setManualFloor } = useStudio()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (!scene || scene.floor.found) return null

  async function apply() {
    if (!scene) return
    const toCam = new Matrix4().fromArray(scene.camera.matrix_world).invert()
    const [a, b, c] = manualFloor.points.map((p) => new Vector3(...p).applyMatrix4(toCam))
    const { normal, d } = planeFromPoints(a, b, c)
    try {
      floorFrameFromPlane(normal, d) // valida que sirva como piso
      if (normal.y < Math.cos((50 * Math.PI) / 180)) throw new Error('inclinado')
    } catch {
      setError('Esos puntos no forman un piso: márcalos sobre el piso, bien separados.')
      setManualFloor({ active: true, points: [] })
      return
    }
    setBusy(true)
    try {
      const updated = await saveManualFloor(scene.id, normal.toArray(), d)
      // conservar los muebles y la escala actuales al reemplazar la escena
      const { placements, scaleK } = useStudio.getState()
      useStudio.setState({ scene: { ...updated, placements, scale_k: scaleK }, manualFloor: { active: false, points: [] } })
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const n = manualFloor.points.length
  return (
    <section data-testid="manual-floor" className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
      <h3 className="font-semibold">No se encontró el piso</h3>
      {!manualFloor.active ? (
        <button onClick={() => setManualFloor({ active: true, points: [] })} className="rounded bg-stone-800 px-2 py-1 text-white">
          Definir piso
        </button>
      ) : (
        <>
          <p className="text-xs">
            {n < 3 ? `Haz clic en 3 puntos del piso en la foto, bien separados (${n}/3).` : 'Listo: aplica el piso.'}
          </p>
          <div className="flex gap-2">
            {n === 3 && (
              <button onClick={apply} disabled={busy} className="rounded bg-stone-800 px-2 py-1 text-white">
                Aplicar
              </button>
            )}
            <button onClick={() => setManualFloor({ active: false, points: [] })} className="text-xs underline">
              Cancelar
            </button>
          </div>
        </>
      )}
      {error && <p className="text-xs text-red-700">{error}</p>}
    </section>
  )
}
