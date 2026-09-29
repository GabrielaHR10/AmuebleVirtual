import { useEffect, useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import { Box3, DoubleSide, Group, Mesh, Vector3, type Material } from 'three'
import type { CatalogItem } from '../api/client'

export interface ModelFit {
  object: Group
  heightM: number
  warning: string | null
}

/**
 * Prepara un GLB para el piso: aplica yaw_offset, centra en x/z, apoya min y en 0 y escala
 * uniforme para que el ANCHO sea el de la ficha (PLAN 2.7). Avisa si el alto difiere > 15 %.
 */
/** Aspecto especial: fantasma (sugerencia) o reflejo en el piso. */
export interface Look {
  opacity: number
  doubleSide?: boolean
}

export function fitModel(source: Group, item: CatalogItem, scaleK: number, look?: Look): ModelFit {
  const inner = source.clone(true)
  inner.traverse((o) => {
    if (o instanceof Mesh) {
      o.castShadow = !look
      o.receiveShadow = !look
      if (look) {
        // material propio (clonado) para no volver transparentes los muebles reales
        const mats = (Array.isArray(o.material) ? o.material : [o.material]).map((m: Material) => {
          const c = m.clone()
          c.transparent = true
          c.opacity = look.opacity
          c.depthWrite = false
          if (look.doubleSide) c.side = DoubleSide // el reflejo (escala y = −1) invierte las caras
          return c
        })
        o.material = Array.isArray(o.material) ? mats : mats[0]
      }
    }
  })
  inner.rotation.y = (item.yaw_offset_deg * Math.PI) / 180
  const wrap = new Group()
  wrap.add(inner)
  wrap.updateMatrixWorld(true)
  const box = new Box3().setFromObject(inner)
  const size = box.getSize(new Vector3())
  const center = box.getCenter(new Vector3())
  inner.position.x -= center.x
  inner.position.z -= center.z
  inner.position.y -= box.min.y
  const targetW = (item.dimensions_cm.width / 100) * scaleK
  const s = size.x > 0 ? targetW / size.x : 1
  wrap.scale.setScalar(s)
  const heightM = size.y * s
  const wantH = (item.dimensions_cm.height / 100) * scaleK
  const warning =
    Math.abs(heightM - wantH) / wantH > 0.15
      ? `El modelo 3D mide ${Math.round(heightM * 100)} cm de alto y la ficha dice ${item.dimensions_cm.height} cm`
      : null
  return { object: wrap, heightM, warning }
}

interface Props {
  item: CatalogItem
  scaleK: number
  onFit?: (fit: ModelFit) => void
  ghost?: boolean
  /** Opacidad del reflejo (> 0 → se dibuja invertido bajo el piso). */
  reflection?: number
}

const GHOST_LOOK: Look = { opacity: 0.45 }

export default function FurnitureModel({ item, scaleK, onFit, ghost = false, reflection = 0 }: Props) {
  const { scene } = useGLTF(item.glb_url!)
  const look = ghost ? GHOST_LOOK : reflection > 0 ? { opacity: reflection, doubleSide: true } : undefined
  const lookKey = look ? `${look.opacity}-${look.doubleSide}` : ''
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fit = useMemo(() => fitModel(scene, item, scaleK, look), [scene, item, scaleK, lookKey])
  useEffect(() => onFit?.(fit), [fit, onFit])
  return <primitive object={fit.object} />
}
