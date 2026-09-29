import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useTexture } from '@react-three/drei'
import { CanvasTexture, Color, DoubleSide, SRGBColorSpace, Vector3, type Group } from 'three'
import type { CatalogItem } from '../api/client'
import { billboardSize } from '../catalog'
import { useStudio } from '../store/useStudio'

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

let reflectionFade: CanvasTexture | null = null

/** Degradado para el reflejo: fuerte junto al piso y se desvanece al alejarse (canal verde = alphaMap). */
function getReflectionFade(): CanvasTexture {
  if (reflectionFade) return reflectionFade
  const c = document.createElement('canvas')
  c.width = 4
  c.height = 128
  const g = c.getContext('2d')!
  const grad = g.createLinearGradient(0, 128, 0, 0) // abajo del lienzo = v 0 = junto al piso
  grad.addColorStop(0, '#ffffff')
  grad.addColorStop(0.35, '#000000')
  grad.addColorStop(1, '#000000')
  g.fillStyle = grad
  g.fillRect(0, 0, 4, 128)
  reflectionFade = new CanvasTexture(c)
  return reflectionFade
}

const tmp = new Vector3()
const FRONT_SHIFT = 0.4 // fracción del fondo que se adelanta el plano hacia la cámara

/**
 * Mueble en "modo recorte 2D": plano con la foto sin fondo, apoyado en el piso, que gira solo en yaw
 * para mirar siempre a la cámara. Sombra de contacto de width × depth (PLAN 2.7).
 */
export default function CutoutBillboard({ item, scaleK, ghost = false }: { item: CatalogItem; scaleK: number; ghost?: boolean }) {
  const texture = useTexture(item.cutout_url!)
  texture.colorSpace = SRGBColorSpace
  const pivot = useRef<Group>(null)
  const reflection = useStudio((s) => s.reflection)
  const light = useStudio((s) => s.light)
  // brillo y tono de la luz del cuarto sobre la foto del mueble (30 % del tinte de la luz ambiente)
  const tint = useMemo(() => {
    const c = new Color(light.hemiColor)
    return [c.r, c.g, c.b].map((v) => light.exposure * (0.7 + 0.3 * v)) as [number, number, number]
  }, [light.hemiColor, light.exposure])
  const shadowOpacity = useStudio((s) => s.shadowOpacity)
  const size = useMemo(() => billboardSize(item), [item])
  const w = size.width * scaleK
  const h = size.height * scaleK
  const footW = (item.dimensions_cm.width / 100) * scaleK
  const footD = (item.dimensions_cm.depth / 100) * scaleK

  useFrame(({ camera }) => {
    const m = pivot.current
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
      <group ref={pivot}>
      {/* la silueta proyecta sombra (el mapa de sombras respeta el alphaTest del recorte) */}
      <mesh position-y={h / 2} renderOrder={2} castShadow={!ghost}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial
          map={texture}
          color={tint}
          transparent
          opacity={ghost ? 0.45 : 1}
          depthWrite={!ghost}
          alphaTest={ghost ? 0.05 : 0.5}
          side={DoubleSide}
          toneMapped={false}
        />
      </mesh>
      {/* reflejo tenue en el piso brillante: la misma foto invertida bajo el piso, desvaneciéndose */}
      {!ghost && reflection > 0 && (
        <mesh position-y={-h / 2} scale-y={-1} renderOrder={1} userData={{ noMask: true }}>
          <planeGeometry args={[w, h]} />
          <meshBasicMaterial
            map={texture}
            alphaMap={getReflectionFade()}
            color={tint}
            transparent
            opacity={reflection}
            depthWrite={false}
            side={DoubleSide}
            toneMapped={false}
          />
        </mesh>
      )}
      </group>
      {/* sombra de contacto: una capa oscura y ajustada justo en la base + una suave más amplia */}
      <mesh rotation-x={-Math.PI / 2} position-y={0.0025} renderOrder={1} userData={{ noMask: true }}>
        <planeGeometry args={[footW * 0.95, footD * 0.8]} />
        <meshBasicMaterial
          map={getContactTexture()}
          transparent
          opacity={Math.min(1, shadowOpacity * 2.2)}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position-y={0.002} renderOrder={1} userData={{ noMask: true }}>
        <planeGeometry args={[footW * 1.25, footD * 1.3]} />
        <meshBasicMaterial
          map={getContactTexture()}
          transparent
          opacity={Math.min(1, shadowOpacity * 1.5)}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
    </>
  )
}
