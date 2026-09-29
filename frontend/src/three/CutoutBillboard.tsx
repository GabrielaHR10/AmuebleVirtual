import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useTexture } from '@react-three/drei'
import { CanvasTexture, DoubleSide, SRGBColorSpace, Vector3, type Mesh } from 'three'
import type { CatalogItem } from '../api/client'
import { billboardSize } from '../catalog'

let contactTexture: CanvasTexture | null = null

/** Degradado radial para la sombra de contacto (generado una sola vez). */
function getContactTexture(): CanvasTexture {
  if (contactTexture) return contactTexture
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')!
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grad.addColorStop(0, 'rgba(0,0,0,1)')
  grad.addColorStop(0.6, 'rgba(0,0,0,0.55)')
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  contactTexture = new CanvasTexture(c)
  return contactTexture
}

const tmp = new Vector3()
const FRONT_SHIFT = 0.4 // fracción del fondo que se adelanta el plano hacia la cámara

/**
 * Mueble en "modo recorte 2D": plano con la foto sin fondo, apoyado en el piso, que gira solo en yaw
 * para mirar siempre a la cámara. Sombra de contacto de width × depth (PLAN 2.7).
 */
export default function CutoutBillboard({ item, scaleK }: { item: CatalogItem; scaleK: number }) {
  const texture = useTexture(item.cutout_url!)
  texture.colorSpace = SRGBColorSpace
  const plane = useRef<Mesh>(null)
  const size = useMemo(() => billboardSize(item), [item])
  const w = size.width * scaleK
  const h = size.height * scaleK
  const footW = (item.dimensions_cm.width / 100) * scaleK
  const footD = (item.dimensions_cm.depth / 100) * scaleK

  useFrame(({ camera }) => {
    const m = plane.current
    if (!m?.parent) return
    // posición de la cámara en coords locales del mueble → girar el plano hacia ella
    m.parent.worldToLocal(camera.getWorldPosition(tmp))
    const angle = Math.atan2(tmp.x, tmp.z)
    m.rotation.y = angle
    // La foto muestra el frente del mueble: su base debe quedar hacia el borde de la huella que ve la cámara
    m.position.x = Math.sin(angle) * footD * FRONT_SHIFT
    m.position.z = Math.cos(angle) * footD * FRONT_SHIFT
  })

  return (
    <>
      <mesh ref={plane} position-y={h / 2} renderOrder={2}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial map={texture} transparent alphaTest={0.5} side={DoubleSide} toneMapped={false} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={0.002} renderOrder={1}>
        <planeGeometry args={[footW * 1.1, footD * 1.1]} />
        <meshBasicMaterial map={getContactTexture()} transparent opacity={0.45} depthWrite={false} toneMapped={false} />
      </mesh>
    </>
  )
}
