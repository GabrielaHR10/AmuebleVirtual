import { useEffect, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import type { Mesh } from 'three'
import { describeHealth, getHealth } from './api/client'

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

function SpinningCube() {
  const ref = useRef<Mesh>(null)
  useFrame((_, dt) => {
    if (ref.current) {
      ref.current.rotation.x += dt * 0.4
      ref.current.rotation.y += dt * 0.6
    }
  })
  return (
    <mesh ref={ref}>
      <boxGeometry args={[1.4, 1.4, 1.4]} />
      <meshStandardMaterial color="#b0825a" />
    </mesh>
  )
}

export default function App() {
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-stone-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold">Estudio Virtual — Santiago Muebles</h1>
        <HealthBadge />
      </header>
      <main className="flex-1">
        <Canvas camera={{ position: [0, 0, 4], fov: 50 }} gl={{ preserveDrawingBuffer: true }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[3, 4, 2]} intensity={1.2} />
          <SpinningCube />
        </Canvas>
      </main>
    </div>
  )
}
