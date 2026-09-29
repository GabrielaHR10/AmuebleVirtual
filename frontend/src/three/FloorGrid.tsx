import { useMemo } from 'react'
import { BufferGeometry, Float32BufferAttribute } from 'three'

/**
 * Cuadrícula de 1 m sobre el piso (mundo del piso, y = 0.002), solo delante de la cámara.
 * No se usa gridHelper porque sus líneas cruzan por detrás de la cámara y no se dibujaban.
 */
export default function FloorGrid({ halfWidth = 8, depth = 14, near = 0.3 }) {
  const geometry = useMemo(() => {
    const pts: number[] = []
    const y = 0.002
    for (let x = -halfWidth; x <= halfWidth; x++) pts.push(x, y, -near, x, y, -depth)
    for (let z = -1; z >= -depth; z--) pts.push(-halfWidth, y, z, halfWidth, y, z)
    const g = new BufferGeometry()
    g.setAttribute('position', new Float32BufferAttribute(pts, 3))
    return g
  }, [halfWidth, depth, near])
  return (
    <lineSegments geometry={geometry} renderOrder={1}>
      <lineBasicMaterial color="#ffffff" transparent opacity={0.6} depthWrite={false} />
    </lineSegments>
  )
}
