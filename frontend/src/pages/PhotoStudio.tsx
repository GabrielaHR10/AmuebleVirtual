import { useEffect, useRef, useState } from 'react'
import { getCatalog, getScene, getScenes, savePlacements, uploadScene, type Scene } from '../api/client'
import CalibrationPanel from '../components/CalibrationPanel'
import CatalogPanel from '../components/CatalogPanel'
import ManualFloorPanel from '../components/ManualFloorPanel'
import RoomEstimateCard from '../components/RoomEstimateCard'
import SelectedPanel from '../components/SelectedPanel'
import Toasts from '../components/Toasts'
import { useEditorKeys } from '../hooks/useEditorKeys'
import { useStudio, type Toggles } from '../store/useStudio'
import Editor3D from '../three/Editor3D'
import { downloadBlob, exportComposite, exportFileName, exportFurnitureMask } from '../three/exportImage'
import FurnitureLayer from '../three/FurnitureLayer'

const TOGGLE_LABELS: [keyof Toggles, string][] = [
  ['occlusion', 'Oclusión'],
  ['grid', 'Cuadrícula 1 m'],
  ['floorMask', 'Máscara de piso'],
  ['shadows', 'Sombras'],
]

function UploadBar({ onScene }: { onScene: (s: Scene) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const pushToast = useStudio((s) => s.pushToast)
  const [scenes, setScenes] = useState<Scene[]>([])
  const current = useStudio((s) => s.scene)

  useEffect(() => {
    getScenes().then(setScenes).catch(() => setScenes([]))
  }, [current?.id])

  async function upload(file: File) {
    setBusy(true)
    try {
      onScene(await uploadScene(file))
    } catch (e) {
      pushToast(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-stone-200 bg-white px-4 py-2 text-sm">
      <input
        ref={input}
        data-testid="upload-input"
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
      />
      <button
        onClick={() => input.current?.click()}
        disabled={busy}
        className="rounded bg-stone-800 px-3 py-1.5 font-medium text-white disabled:opacity-60"
      >
        {busy ? 'Analizando la foto… (~10–30 s)' : 'Subir foto'}
      </button>
      <label className="flex items-center gap-2">
        Escenas anteriores
        <select
          data-testid="scene-select"
          className="max-w-64 rounded border border-stone-300 px-2 py-1"
          value={current?.id ?? ''}
          onChange={(e) =>
            e.target.value &&
            getScene(e.target.value)
              .then(onScene)
              .catch((err: unknown) => pushToast(err instanceof Error ? err.message : String(err)))
          }
        >
          <option value="">—</option>
          {scenes.map((s) => (
            <option key={s.id} value={s.id}>
              {s.created_at?.slice(0, 16).replace('T', ' ') ?? s.id}
            </option>
          ))}
        </select>
      </label>
      {current && <ExportButtons />}
    </div>
  )
}

function ExportButtons() {
  const scene = useStudio((s) => s.scene)
  const select = useStudio((s) => s.select)
  const pushToast = useStudio((s) => s.pushToast)
  const [busy, setBusy] = useState(false)
  if (!scene) return null
  const { url, width, height } = scene.image

  async function run(kind: 'png' | 'mask') {
    setBusy(true)
    select(null) // sin selección: no se exportan contornos ni etiquetas
    try {
      await new Promise((r) => requestAnimationFrame(() => r(null)))
      const blob = kind === 'png' ? await exportComposite(url, width, height) : await exportFurnitureMask(width, height)
      downloadBlob(blob, exportFileName(kind === 'png' ? 'amoblado' : 'mascara_muebles'))
    } catch (e) {
      pushToast(`No se pudo exportar: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ml-auto flex items-center gap-2">
      <button
        onClick={() => run('mask')}
        disabled={busy}
        className="rounded px-2 py-1.5 text-xs text-stone-500 underline disabled:opacity-60"
        title="Blanco sobre negro, para el retoque con IA"
      >
        Máscara de muebles
      </button>
      <button
        onClick={() => run('png')}
        disabled={busy}
        className="rounded bg-emerald-700 px-3 py-1.5 font-medium text-white disabled:opacity-60"
      >
        {busy ? 'Exportando…' : 'Exportar PNG'}
      </button>
    </div>
  )
}

function ViewSliders() {
  const { shadowOpacity, exposure, setView } = useStudio()
  return (
    <div className="mt-2 space-y-1 text-xs">
      <label className="block">
        Intensidad de sombra: {Math.round(shadowOpacity * 100)} %
        <input
          type="range"
          min={0}
          max={0.8}
          step={0.05}
          value={shadowOpacity}
          onChange={(e) => setView({ shadowOpacity: Number(e.target.value) })}
          className="w-full"
        />
      </label>
      <label className="block">
        Exposición de muebles: {exposure.toFixed(2)}
        <input
          type="range"
          min={0.5}
          max={1.5}
          step={0.05}
          value={exposure}
          onChange={(e) => setView({ exposure: Number(e.target.value) })}
          className="w-full"
        />
      </label>
    </div>
  )
}

/** Guarda los muebles 1 s después del último cambio (PLAN 2.7). */
function useAutosave() {
  const { scene, placements, scaleK } = useStudio()
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  useEffect(() => {
    if (!scene) return
    if (placements === scene.placements && scaleK === scene.scale_k) return
    const t = setTimeout(() => {
      setStatus('saving')
      savePlacements(scene.id, placements, scaleK)
        .then(() => setStatus('saved'))
        .catch((e: unknown) => {
          setStatus('error')
          useStudio.getState().pushToast(`No se pudieron guardar los cambios: ${e instanceof Error ? e.message : e}`)
        })
    }, 1000)
    return () => clearTimeout(t)
  }, [scene, placements, scaleK])
  return status
}

export default function PhotoStudio() {
  const { scene, setScene, setCatalog, toggles, toggle, select } = useStudio()
  const saveStatus = useAutosave()
  useEditorKeys(!!scene)

  useEffect(() => {
    getCatalog().then(setCatalog).catch(() => setCatalog([]))
  }, [setCatalog])

  return (
    <div className="flex h-full flex-col">
      <Toasts />
      <UploadBar onScene={setScene} />
      <div className="flex min-h-0 flex-1">
        {scene && <CatalogPanel />}
        <div className="relative min-w-0 flex-1">
          {scene ? (
            <Editor3D scene={scene} toggles={toggles} onFloorPointerMissed={() => select(null)}>
              <FurnitureLayer />
            </Editor3D>
          ) : (
            <div className="flex h-full items-center justify-center text-stone-500">
              Sube una foto del espacio (idealmente vacío) para empezar.
            </div>
          )}
        </div>
        {scene && (
          <aside className="w-72 space-y-3 overflow-y-auto border-l border-stone-200 bg-stone-50 p-3">
            <ManualFloorPanel />
            <SelectedPanel />
            <p data-testid="save-status" className="text-xs text-stone-500">
              {{ idle: '', saving: 'Guardando…', saved: 'Cambios guardados', error: 'No se pudo guardar' }[saveStatus]}
            </p>
            <section className="rounded-lg border border-stone-200 bg-white p-3 text-sm">
              <h3 className="mb-1 font-semibold">Vista</h3>
              {TOGGLE_LABELS.map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 py-0.5">
                  <input type="checkbox" checked={toggles[key]} onChange={() => toggle(key)} />
                  {label}
                </label>
              ))}
              <ViewSliders />
            </section>
            <CalibrationPanel />
            <RoomEstimateCard scene={scene} />
          </aside>
        )}
      </div>
    </div>
  )
}
