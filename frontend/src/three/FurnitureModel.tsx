import { useEffect, useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import { Box3, Group, Mesh, Vector3 } from 'three'
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
export function fitModel(source: Group, item: CatalogItem, scaleK: number): ModelFit {
  const inner = source.clone(true)
  inner.traverse((o) => {
    if (o instanceof Mesh) {
      o.castShadow = true
      o.receiveShadow = true
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
}

export default function FurnitureModel({ item, scaleK, onFit }: Props) {
  const { scene } = useGLTF(item.glb_url!)
  const fit = useMemo(() => fitModel(scene, item, scaleK), [scene, item, scaleK])
  useEffect(() => onFit?.(fit), [fit, onFit])
  return <primitive object={fit.object} />
}
