import { useEffect, useRef, useState } from 'react'
import { createKeyframeScenes, getScene, getVideo, uploadVideo, waitJob, type Job, type VideoMeta } from '../api/client'
import { useStudio } from '../store/useStudio'
import VideoClip from './VideoClip'

const LAST_VIDEO_KEY = 'estudio.lastVideo'

function ProgressBar({ job }: { job: Job | null }) {
  if (!job) return null
  return (
    <div data-testid="video-progress" className="space-y-1">
      <div className="h-2 overflow-hidden rounded bg-stone-200">
        <div className="h-full bg-sky-600 transition-all" style={{ width: `${Math.round(job.progress * 100)}%` }} />
      </div>
      <p className="text-xs text-stone-600">{job.message}</p>
    </div>
  )
}

/** Página Video (PLAN 5.1): fotogramas clave del recorrido → escenas para amoblar en el Estudio. */
export default function VideoStudio({ onOpenScene }: { onOpenScene: () => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [meta, setMeta] = useState<VideoMeta | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const { setScene, pushToast } = useStudio()

  useEffect(() => {
    let id: string | null = null
    try {
      id = localStorage.getItem(LAST_VIDEO_KEY)
    } catch {
      // sin almacenamiento
    }
    if (id) getVideo(id).then(setMeta).catch(() => undefined)
  }, [])

  async function run<T>(fn: () => Promise<T>) {
    setBusy(true)
    try {
      return await fn()
    } catch (e) {
      pushToast(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      setJob(null)
    }
  }

  const upload = (file: File) =>
    run(async () => {
      setMeta(null)
      const { video_id, job_id } = await uploadVideo(file)
      try {
        localStorage.setItem(LAST_VIDEO_KEY, video_id)
      } catch {
        // sin almacenamiento
      }
      await waitJob(job_id, setJob)
      setMeta(await getVideo(video_id))
    })

  const createScenes = () =>
    run(async () => {
      if (!meta) return
      const ks = meta.keyframes.filter((k) => k.floor_ratio > 0 && !k.scene_id).map((k) => k.k)
      const { job_id } = await createKeyframeScenes(meta.video_id, ks)
      await waitJob(job_id, setJob)
      setMeta(await getVideo(meta.video_id))
    })

  const open = (sceneId: string) =>
    run(async () => {
      setScene(await getScene(sceneId))
      onOpenScene()
    })

  const pending = meta?.keyframes.some((k) => k.floor_ratio > 0 && !k.scene_id)
  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">Amoblar desde un video</h2>
        <p className="text-sm text-stone-600">
          Sube un recorrido del espacio (hasta 3 minutos). Se eligen los fotogramas más nítidos donde se ve el piso,
          y cada uno se puede amoblar como una foto. Consejos: video horizontal, movimiento lento, que se vean piso,
          puertas y ventanas.
        </p>
        <input
          ref={input}
          data-testid="video-input"
          type="file"
          accept="video/mp4,video/quicktime"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
        />
        <button
          onClick={() => input.current?.click()}
          disabled={busy}
          className="rounded bg-stone-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
        >
          Subir video
        </button>
        <ProgressBar job={job} />
      </section>

      {meta && meta.keyframes.length > 0 && (
        <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold">Fotogramas ({Math.round(meta.duration_s)} s de video)</h2>
            {pending && (
              <button onClick={createScenes} disabled={busy} className="rounded bg-sky-700 px-3 py-1.5 text-sm text-white disabled:opacity-60">
                Preparar fotogramas para amoblar
              </button>
            )}
          </div>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {meta.keyframes.map((k) => (
              <li key={k.k} data-testid="keyframe" className="space-y-1 text-xs">
                <img src={k.url} alt={`Fotograma a los ${k.time_s} s`} className="aspect-[9/16] w-full rounded object-cover" />
                <p className="text-stone-600">
                  {Math.floor(k.time_s / 60)}:{String(Math.round(k.time_s % 60)).padStart(2, '0')}
                  {k.floor_ratio === 0 && <span className="ml-1 text-amber-700">· sin piso visible</span>}
                </p>
                {k.scene_id && (
                  <button onClick={() => open(k.scene_id!)} className="w-full rounded bg-emerald-700 py-1 text-white">
                    Amoblar este fotograma
                  </button>
                )}
              </li>
            ))}
          </ul>
          {meta.summary && (
            <p data-testid="video-summary" className="rounded bg-stone-50 p-2 text-sm text-stone-700">
              Medidas aproximadas del recorrido: techo ≈ {meta.summary.ceiling_height_m?.toFixed(2) ?? '—'} m · mayor
              ancho visible ≈ {meta.summary.max_width_m?.toFixed(1) ?? '—'} m · mayor fondo visible ≈{' '}
              {meta.summary.max_depth_m?.toFixed(1) ?? '—'} m (cada fotograma ve solo una parte).
            </p>
          )}
        </section>
      )}

      {meta && <VideoClip key={meta.video_id} meta={meta} onOpenScene={onOpenScene} />}
    </div>
  )
}
