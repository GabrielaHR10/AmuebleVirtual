import { useState } from 'react'
import { scaleFromCalibration, useStudio } from '../store/useStudio'

/** "Calibrar medida" (PLAN 2.8): 2 clics en el piso + distancia real → scale_k. */
export default function CalibrationPanel() {
  const { calibration, setCalibration, scaleK, setScaleK } = useStudio()
  const [real, setReal] = useState('')
  const [error, setError] = useState<string | null>(null)

  function apply() {
    const k = scaleFromCalibration(calibration.points, Number(real))
    if (k == null) {
      setError('Revisa la distancia: el resultado no es razonable.')
      return
    }
    setScaleK(k)
    setCalibration({ active: false, points: [] })
    setReal('')
    setError(null)
  }

  return (
    <section data-testid="calibration" className="space-y-2 rounded-lg border border-stone-200 bg-white p-3 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Escala</h3>
        <span className="text-xs text-stone-500">actual: {scaleK.toFixed(3)}</span>
      </div>
      {!calibration.active ? (
        <div className="flex gap-2">
          <button
            onClick={() => setCalibration({ active: true, points: [] })}
            className="rounded bg-stone-100 px-2 py-1"
          >
            Calibrar medida
          </button>
          {scaleK !== 1 && (
            <button onClick={() => setScaleK(1)} className="rounded px-2 py-1 text-stone-500 underline">
              Restablecer
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="text-xs text-stone-600">
            {calibration.points.length < 2
              ? `Haz clic en ${calibration.points.length === 0 ? 'dos puntos' : 'el segundo punto'} del piso cuya distancia real conozcas (p. ej. el ancho de una puerta o de una baldosa).`
              : 'Escribe la distancia real entre los dos puntos:'}
          </p>
          {calibration.points.length === 2 && (
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                value={real}
                onChange={(e) => setReal(e.target.value)}
                placeholder="cm"
                className="w-24 rounded border border-stone-300 px-2 py-1"
              />
              <button onClick={apply} className="rounded bg-stone-800 px-2 py-1 text-white">
                Aplicar
              </button>
            </div>
          )}
          {error && <p className="text-xs text-red-700">{error}</p>}
          <button
            onClick={() => setCalibration({ active: false, points: [] })}
            className="text-xs text-stone-500 underline"
          >
            Cancelar
          </button>
        </>
      )}
    </section>
  )
}
