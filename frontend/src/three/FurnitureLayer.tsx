import { useCallback, useEffect, useRef } from 'react'
import { type ThreeEvent } from '@react-three/fiber'
import { Html, Line } from '@react-three/drei'
import type { Object3D } from 'three'
import type { CatalogItem, Placement } from '../api/client'
import { billboardSize, formatDims } from '../catalog'
import { useStudio } from '../store/useStudio'
import CutoutBillboard from './CutoutBillboard'
import type { FitResult } from './fit'
import FurnitureModel, { type ModelFit } from './FurnitureModel'
import { useFits } from './useFits'

// Todo lo de aquí vive DENTRO del grupo del piso: y = 0 es el piso, metros (PLAN §4).

/** Punto (x, z) donde el rayo del puntero toca el piso, en coords del grupo del piso. */
function rayToFloor(e: ThreeEvent<PointerEvent>, group: Object3D): [number, number] | null {
  const o = group.worldToLocal(e.ray.origin.clone())
  const dir = group.worldToLocal(e.ray.origin.clone().add(e.ray.direction)).sub(o)
  if (dir.y >= -1e-6) return null
  const t = -o.y / dir.y
  return [o.x + dir.x * t, o.z + dir.z * t]
}

interface Drag {
  uid: string
  dx: number
  dz: number
  before: Placement[]
}

function Footprint({ w, d, ok }: { w: number; d: number; ok: boolean }) {
  const y = 0.004
  const pts: [number, number, number][] = [
    [-w / 2, y, -d / 2],
    [w / 2, y, -d / 2],
    [w / 2, y, d / 2],
    [-w / 2, y, d / 2],
    [-w / 2, y, -d / 2],
  ]
  return <Line points={pts} color={ok ? '#22c55e' : '#ef4444'} lineWidth={2.5} depthTest={false} renderOrder={3} />
}

interface PlacedProps {
  p: Placement
  item: CatalogItem
  selected: boolean
  fit: FitResult | undefined
  scaleK: number
  onDown: (e: ThreeEvent<PointerEvent>, p: Placement) => void
}

function Placed({ p, item, selected, fit, scaleK, onDown }: PlacedProps) {
  const setModelWarning = useStudio((s) => s.setModelWarning)
  const onFit = useCallback((f: ModelFit) => setModelWarning(item.id, f.warning), [item.id, setModelWarning])
  const w = (item.dimensions_cm.width / 100) * scaleK
  const d = (item.dimensions_cm.depth / 100) * scaleK
  const labelY = p.mode === 'cutout' ? billboardSize(item).height * scaleK : (item.dimensions_cm.height / 100) * scaleK
  const ok = fit?.ok ?? true
  return (
    <group position={[p.x, 0, p.z]} rotation-y={(p.yaw_deg * Math.PI) / 180} onPointerDown={(e) => onDown(e, p)}>
      {p.mode === '3d' && item.glb_url ? (
        <FurnitureModel item={item} scaleK={scaleK} onFit={onFit} />
      ) : (
        <CutoutBillboard item={item} scaleK={scaleK} />
      )}
      {(selected || !ok) && <Footprint w={w} d={d} ok={ok} />}
      {selected && (
        <Html position={[0, labelY + 0.12, 0]} center zIndexRange={[20, 0]} style={{ pointerEvents: 'none' }}>
          <div className="whitespace-nowrap rounded bg-black/70 px-2 py-0.5 text-xs text-white">
            {formatDims(item.dimensions_cm)}
            {!ok && fit?.message ? <span className="ml-1 text-red-300">· {fit.message}</span> : null}
          </div>
        </Html>
      )}
    </group>
  )
}

export default function FurnitureLayer() {
  const { placements, catalog, selectedUid, scaleK, select, preview, commitFrom } = useStudio()
  const fits = useFits()
  const drag = useRef<Drag | null>(null)
  const floorGroup = useRef<Object3D | null>(null)

  useEffect(() => {
    const end = () => {
      if (drag.current) commitFrom(drag.current.before)
      drag.current = null
    }
    window.addEventListener('pointerup', end)
    return () => window.removeEventListener('pointerup', end)
  }, [commitFrom])

  const onDown = useCallback(
    (e: ThreeEvent<PointerEvent>, p: Placement) => {
      e.stopPropagation()
      select(p.uid)
      const group = floorGroup.current
      if (!group) return
      const hit = rayToFloor(e, group)
      if (!hit) return
      drag.current = { uid: p.uid, dx: p.x - hit[0], dz: p.z - hit[1], before: useStudio.getState().placements }
    },
    [select],
  )

  const onMove = useCallback(
    (e: ThreeEvent<PointerEvent>) => {
      const d = drag.current
      const group = floorGroup.current
      if (!d || !group) return
      const hit = rayToFloor(e, group)
      if (!hit) return
      const cur = useStudio.getState().placements
      preview(cur.map((p) => (p.uid === d.uid ? { ...p, x: hit[0] + d.dx, z: hit[1] + d.dz } : p)))
    },
    [preview],
  )

  const byId = new Map(catalog.map((i) => [i.id, i]))
  return (
    <>
      {/* Plano invisible de arrastre (raycast contra y = 0) */}
      <mesh
        rotation-x={-Math.PI / 2}
        onPointerMove={onMove}
        onUpdate={(m) => (floorGroup.current = m.parent)}
      >
        <planeGeometry args={[60, 60]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
      </mesh>
      {placements.map((p) => {
        const item = byId.get(p.item_id)
        if (!item) return null
        return (
          <Placed
            key={p.uid}
            p={p}
            item={item}
            selected={p.uid === selectedUid}
            fit={fits[p.uid]}
            scaleK={scaleK}
            onDown={onDown}
          />
        )
      })}
    </>
  )
}
