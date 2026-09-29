import { useLayoutEffect } from 'react'
import { useGLTF } from '@react-three/drei'
import { Mesh, MeshBasicMaterial } from 'three'

// Malla de la foto (coords de cámara) que solo escribe profundidad: tapa los muebles que quedan detrás
// de paredes u objetos reales. Va FUERA del grupo del piso (PLAN §4).
const material = new MeshBasicMaterial({ colorWrite: false })

export default function OcclusionMesh({ url }: { url: string }) {
  const { scene } = useGLTF(url)
  useLayoutEffect(() => {
    scene.traverse((o) => {
      if (o instanceof Mesh) {
        o.material = material
        o.renderOrder = -1
        o.frustumCulled = false
      }
    })
  }, [scene])
  return <primitive object={scene} />
}
