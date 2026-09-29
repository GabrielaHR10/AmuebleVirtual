import { useEffect, useState } from 'react'
import { describeHealth, getHealth } from './api/client'
import CatalogAdmin from './pages/CatalogAdmin'
import PhotoStudio from './pages/PhotoStudio'
import VideoStudio from './pages/VideoStudio'

type Status = { state: 'loading' } | { state: 'ok'; text: string } | { state: 'error'; text: string }

function HealthBadge() {
  const [status, setStatus] = useState<Status>({ state: 'loading' })

  useEffect(() => {
    const ctrl = new AbortController()
    getHealth(ctrl.signal)
      .then((h) => setStatus({ state: 'ok', text: describeHealth(h) }))
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return
        const msg = e instanceof Error ? e.message : String(e)
        setStatus({ state: 'error', text: `Sin conexión con el servidor (${msg})` })
      })
    return () => ctrl.abort()
  }, [])

  const color =
    status.state === 'ok' ? 'bg-emerald-500' : status.state === 'error' ? 'bg-red-500' : 'bg-amber-400'
  const text = status.state === 'loading' ? 'Conectando con el servidor…' : status.text

  return (
    <span data-testid="health" className="inline-flex items-center gap-2 text-sm text-stone-600">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      {text}
    </span>
  )
}

type Page = 'studio' | 'video' | 'catalog'
const PATHS: Record<Page, string> = { studio: '/', video: '/video', catalog: '/catalogo' }

function pageFromPath(path: string): Page {
  return path.startsWith('/catalogo') ? 'catalog' : path.startsWith('/video') ? 'video' : 'studio'
}

export default function App() {
  const [page, setPage] = useState<Page>(() => pageFromPath(window.location.pathname))

  useEffect(() => {
    const onPop = () => setPage(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  function go(p: Page) {
    window.history.pushState(null, '', PATHS[p])
    setPage(p)
  }

  const tab = (p: Page, label: string) => (
    <button
      onClick={() => go(p)}
      className={`rounded px-3 py-1.5 text-sm ${page === p ? 'bg-stone-800 text-white' : 'text-stone-600 hover:bg-stone-100'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-stone-200 bg-white px-6 py-3">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-semibold">Estudio Virtual — Santiago Muebles</h1>
          <nav className="flex gap-1">
            {tab('studio', 'Estudio')}
            {tab('video', 'Video')}
            {tab('catalog', 'Catálogo')}
          </nav>
        </div>
        <HealthBadge />
      </header>
      <main className={`min-h-0 flex-1 ${page === 'studio' ? 'overflow-hidden' : 'overflow-auto'}`}>
        {page === 'catalog' ? <CatalogAdmin /> : page === 'video' ? <VideoStudio onOpenScene={() => go('studio')} /> : <PhotoStudio />}
      </main>
    </div>
  )
}
