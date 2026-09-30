import { useMemo } from 'react'
import { Environment, useTexture } from '@react-three/drei'
import { BackSide, Color, SRGBColorSpace } from 'three'
import type { Scene } from '../api/client'

/**
 * Luz de entorno hecha con la propia foto (R.3): la foto va frente a la cámara, exactamente con su campo
 * de visión, y el resto de la esfera toma el color promedio del cuarto (paredes arriba, piso abajo).
 * Así los muebles reciben la luz y los colores reales del espacio en vez de los de un HDRI genérico.
 */
export default function PhotoEnvironment({ scene, intensity = 0.8 }: { scene: Scene; intensity?: number }) {
  const photo = useTexture(scene.image.url)
  photo.colorSpace = SRGBColorSpace
  const aspect = scene.image.width / scene.image.height
  const dist = 20
  const h = 2 * dist * Math.tan((scene.camera.fov_y_deg * Math.PI) / 360)
  const w = h * aspect
  const { wall, floor } = useMemo(() => {
    const f = scene.lighting?.floor_rgb ?? [150, 140, 130]
    const floorColor = new Color(f[0] / 255, f[1] / 255, f[2] / 255)
    // paredes: blanco teñido levemente por el tono del piso (reflejo típico de un cuarto claro)
    const wallColor = new Color(1, 1, 1).lerp(floorColor, 0.15).multiplyScalar(0.85)
    return { wall: wallColor, floor: floorColor }
  }, [scene])

  return (
    <Environment resolution={128} environmentIntensity={intensity} background={false} frames={1}>
      {/* esfera: arriba y alrededor el color de las paredes */}
      <mesh>
        <sphereGeometry args={[dist * 2, 32, 16]} />
        <meshBasicMaterial color={wall} side={BackSide} toneMapped={false} />
      </mesh>
      {/* abajo, el piso */}
      <mesh rotation-x={-Math.PI / 2} position-y={-dist * 0.5}>
        <planeGeometry args={[dist * 8, dist * 8]} />
        <meshBasicMaterial color={floor} toneMapped={false} />
      </mesh>
      {/* delante, la foto con el mismo encuadre de la cámara */}
      <mesh position-z={-dist}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial map={photo} toneMapped={false} />
      </mesh>
    </Environment>
  )
}
