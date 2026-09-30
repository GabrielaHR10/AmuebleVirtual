import { useCallback, useEffect, useState } from 'react'
import {
  composeClip,
  createClip,
  getCatalog,
  getClip,
  getScene,
  uploadClipFrame,
  waitJob,
  type CatalogItem,
  type ClipTrack,
  type Job,
  type Scene,
  type VideoMeta,
} from '../api/client'
import { useStudio } from '../store/useStudio'
import VideoRenderer from '../three/VideoRenderer'

const clipKey = (videoId: string) => `estudio.clip.${videoId}`

function readClipId(videoId: string): string | null {
  try {
    return localStorage.getItem(clipKey(videoId))
  } catch {
    return null
  }
}

interface Render {
  scene: Scene
  catalog: CatalogItem[]
}

/** Video con muebles (R.5): un tramo del recorrido con los muebles elegidos, siguiendo la cámara. */
export default function VideoClip({ meta, onOpenScene }: { meta: VideoMeta; onOpenScene: () => void }) {
  const [t0, setT0] = useState(0)
  const [t1, setT1] = useState(Math.min(10, Math.floor(meta.duration_s)))
  const [clip, setClip] = useState<ClipTrack | null>(null)
  const [status, setStatus] = useState<{ progress: number; message: string } | null>(null)
  const [render, setRender] = useState<Render | null>(null)
  const { setScene, pushToast } = useStudio()
  const busy = status !== null

  useEffect(() => {
    const id = readClipId(meta.video_id)
    if (id) getClip(meta.video_id, id).then(setClip).catch(() => undefined)
  }, [meta.video_id])

  const onJob = (j: Job) => setStatus({ progress: j.progress, message: j.message })
  const fail = useCallback(
    (e: unknown) => {
      pushToast(e instanceof Error ? e.message : String(e))
      setStatus(null)
      setRender(null)
    },
    [pushToast],
  )

  async function prepare() {
    try {
      setStatus({ progress: 0, message: 'Empezando…' })
      const { clip_id, job_id } = await createClip(meta.video_id, t0, t1)
      await waitJob(job_id, onJob)
      try {
        localStorage.setItem(clipKey(meta.video_id), clip_id)
      } catch {
        // sin almacenamiento
      }
      setClip(await getClip(meta.video_id, clip_id))
      setStatus(null)
    } catch (e) {
      fail(e)
    }
  }

  async function furnish() {
    if (!clip) return
    try {
      setScene(await getScene(clip.ref_scene_id))
      onOpenScene()
    } catch (e) {
      fail(e)
    }
  }

  async function startRender() {
    if (!clip) return
    try {
      const [scene, catalog] = await Promise.all([getScene(clip.ref_scene_id), getCatalog()])
      if (!scene.floor.frame) throw new Error('No se detectó el piso en el fotograma de referencia.')
      if (scene.placements.length === 0) {
        throw new Error('Primero amobla el fotograma de referencia (botón «Elegir muebles») y guarda.')
      }
      setStatus({ progress: 0, message: 'Dibujando los muebles en cada fotograma…' })
      setRender({ scene, catalog })
    } catch (e) {
      fail(e)
    }
  }

  const upload = useCallback(
    (k: number, color: Blob, depth: Blob) => uploadClipFrame(clip!.video_id, clip!.clip_id, k, color, depth),
    [clip],
  )
  const onProgress = useCallback(
    (done: number, total: number) =>
      setStatus({ progress: 0.7 * (done / total), message: `Dibujando los muebles… (${done}/${total})` }),
    [],
  )
  const onDone = useCallback(async () => {
    if (!clip) return
    setRender(null)
    try {
      const { job_id } = await composeClip(clip.video_id, clip.clip_id)
      await waitJob(job_id, (j) => setStatus({ progress: 0.7 + 0.3 * j.progress, message: j.message }))
      setClip(await getClip(clip.video_id, clip.clip_id))
      setStatus(null)
    } catch (e) {
      fail(e)
    }
  }, [clip, fail])

  const ref = clip?.frames[clip.ref_index]
  return (
    <section data-testid="video-clip" className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
      <h2 className="font-semibold">Video con muebles</h2>
      <p className="text-sm text-stone-600">
        Elige un tramo corto (2 a 20 s, movimiento lento). Se sigue el movimiento de la cámara, amoblas un fotograma
        y los muebles aparecen en todo el tramo, a su tamaño real y tapados por lo que esté delante.
      </p>
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="space-y-1">
          <span className="block text-stone-600">Desde (s)</span>
          <input type="number" min={0} step={0.1} value={t0} onChange={(e) => setT0(Number(e.target.value))}
            className="w-24 rounded border border-stone-300 px-2 py-1" data-testid="clip-t0" />
        </label>
        <label className="space-y-1">
          <span className="block text-stone-600">Hasta (s)</span>
          <input type="number" min={0} step={0.1} value={t1} onChange={(e) => setT1(Number(e.target.value))}
            className="w-24 rounded border border-stone-300 px-2 py-1" data-testid="clip-t1" />
        </label>
        <button onClick={prepare} disabled={busy}
          className="rounded bg-stone-800 px-3 py-1.5 font-medium text-white disabled:opacity-60">
          Preparar tramo (~2–4 min)
        </button>
      </div>

      {status && (
        <div data-testid="clip-progress" className="space-y-1">
          <div className="h-2 overflow-hidden rounded bg-stone-200">
            <div className="h-full bg-sky-600 transition-all" style={{ width: `${Math.round(status.progress * 100)}%` }} />
          </div>
          <p className="text-xs text-stone-600">{status.message}</p>
        </div>
      )}

      {clip && ref && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <p className="text-sm text-stone-700">
              Tramo {clip.t0.toFixed(1)}–{clip.t1.toFixed(1)} s · {clip.frames.length} fotogramas. Fotograma de
              referencia ({ref.t.toFixed(1)} s):
            </p>
            <img src={ref.url} alt="Fotograma de referencia" className="max-h-72 rounded" />
            <div className="flex flex-wrap gap-2">
              <button onClick={furnish} disabled={busy} className="rounded bg-emerald-700 px-3 py-1.5 text-sm text-white disabled:opacity-60">
                1 · Elegir muebles
              </button>
              <button onClick={startRender} disabled={busy} data-testid="clip-render"
                className="rounded bg-sky-700 px-3 py-1.5 text-sm text-white disabled:opacity-60">
                2 · Crear video con muebles
              </button>
            </div>
          </div>
          {clip.video_url && (
            <div className="space-y-2">
              <video data-testid="clip-video" src={clip.video_url} controls loop playsInline className="max-h-96 rounded" />
              <a href={clip.video_url} download="video_amoblado.mp4" className="text-sm text-sky-700 underline">
                Descargar video
              </a>
            </div>
          )}
        </div>
      )}

      {render && clip && (
        <VideoRenderer track={clip} scene={render.scene} catalog={render.catalog}
          upload={upload} onProgress={onProgress} onDone={onDone} onError={fail} />
      )}
    </section>
  )
}
