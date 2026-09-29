import { useStudio } from '../store/useStudio'

export default function Toasts() {
  const { toasts, dismissToast } = useStudio()
  if (!toasts.length) return null
  return (
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className="pointer-events-auto flex items-start gap-3 rounded-lg bg-red-700 px-4 py-2 text-sm text-white shadow-lg"
        >
          <span>{t.text}</span>
          <button onClick={() => dismissToast(t.id)} className="text-white/80" aria-label="Cerrar">
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
