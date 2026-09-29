import { useCallback, useEffect, useRef } from 'react'
import { type ThreeEvent } from '@react-three/fiber'
import { Html, Line } from '@react-three/drei'
import type { Object3D } from 'three'
import type { CatalogItem, Placement } from '../api/client'
import { billboardSize, formatDims } from '../catalog'
import { useStudio } from '../store/useStudio'
import CutoutBillboard from './CutoutBillboard'
import { HelperGroup, markHelper } from './exportImage'
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

/** Puntos y línea de la calibración, con la distancia medida en la escena. */
function CalibrationMarks() {
  const calibration = useStudio((s) => s.calibration) // (un selector que cree arreglos nuevos cicla en zustand v5)
  const points = calibration.active ? calibration.points : []
  if (!points.length) return null
  const y = 0.01
  const pts = points.map(([x, z]) => [x, y, z] as [number, number, number])
  const dist = points.length === 2 ? Math.hypot(points[1][0] - points[0][0], points[1][1] - points[0][1]) : null
  return (
    <HelperGroup>
      {pts.map((p, i) => (
        <mesh key={i} position={p} renderOrder={4}>
          <sphereGeometry args={[0.04, 16, 16]} />
          <meshBasicMaterial color="#f59e0b" depthTest={false} />
        </mesh>
      ))}
      {pts.length === 2 && (
        <>
          <Line points={pts} color="#f59e0b" lineWidth={3} depthTest={false} renderOrder={4} />
          <Html position={[(pts[0][0] + pts[1][0]) / 2, 0.15, (pts[0][2] + pts[1][2]) / 2]} center>
            <div className="whitespace-nowrap rounded bg-amber-500 px-2 py-0.5 text-xs font-medium text-white">
              {Math.round(dist! * 100)} cm en la foto
            </div>
          </Html>
        </>
      )}
    </HelperGroup>
  )
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
  return (
    <Line ref={markHelper} points={pts} color={ok ? '#22c55e' : '#ef4444'} lineWidth={2.5} depthTest={false} renderOrder={3} />
  )
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
    <group
      position={[p.x, 0, p.z]}
      rotation-y={(p.yaw_deg * Math.PI) / 180}
      onPointerDown={(e) => onDown(e, p)}
      userData={{ furniture: true }}
    >
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

/** Sugerencia pendiente: semitransparente, con su huella en azul y sin interacción. */
function Ghost({ p, item, scaleK }: { p: Placement; item: CatalogItem; scaleK: number }) {
  const w = (item.dimensions_cm.width / 100) * scaleK
  const d = (item.dimensions_cm.depth / 100) * scaleK
  const y = 0.004
  const pts: [number, number, number][] = [
    [-w / 2, y, -d / 2], [w / 2, y, -d / 2], [w / 2, y, d / 2], [-w / 2, y, d / 2], [-w / 2, y, -d / 2],
  ]
  return (
    <group position={[p.x, 0, p.z]} rotation-y={(p.yaw_deg * Math.PI) / 180} userData={{ ghost: true }}>
      {p.mode === '3d' && item.glb_url ? (
        <FurnitureModel item={item} scaleK={scaleK} ghost />
      ) : (
        <CutoutBillboard item={item} scaleK={scaleK} ghost />
      )}
      <Line ref={markHelper} points={pts} color="#38bdf8" lineWidth={2} dashed dashSize={0.1} gapSize={0.06} depthTest={false} renderOrder={3} />
    </group>
  )
}

export default function FurnitureLayer() {
  const { placements, catalog, selectedUid, scaleK, select, preview, commitFrom, ghosts } = useStudio()
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
      if (useStudio.getState().calibration.active) return // en calibración el clic marca el piso
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

  const onFloorClick = useCallback((e: ThreeEvent<MouseEvent>) => {
    const { calibration, setCalibration } = useStudio.getState()
    const group = floorGroup.current
    if (!calibration.active || !group) return
    e.stopPropagation()
    const local = group.worldToLocal(e.point.clone())
    const points = calibration.points.length >= 2 ? [] : calibration.points
    setCalibration({ active: true, points: [...points, [local.x, local.z]] })
  }, [])

  const byId = new Map(catalog.map((i) => [i.id, i]))
  return (
    <>
      <CalibrationMarks />
      {/* Plano invisible de arrastre (raycast contra y = 0) */}
      <mesh
        rotation-x={-Math.PI / 2}
        onPointerMove={onMove}
        onClick={onFloorClick}
        onUpdate={(m) => (floorGroup.current = m.parent)}
      >
        <planeGeometry args={[60, 60]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
      </mesh>
      {ghosts?.placements.map((g) => {
        const item = byId.get(g.item_id)
        return item ? <Ghost key={g.uid} p={g} item={item} scaleK={scaleK} /> : null
      })}
      {placements.map((p) => {
        const item = byId.get(p.item_id)
        // los muebles que se están reacomodando se ocultan mientras se ven los fantasmas
        if (!item || ghosts?.replaceUids.includes(p.uid)) return null
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
