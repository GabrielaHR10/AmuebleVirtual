import { useMemo } from 'react'
import { BufferGeometry, Float32BufferAttribute } from 'three'
import { useStudio } from '../store/useStudio'
import { markHelper } from './exportImage'

/**
 * Cuadrícula de 1 m sobre el piso (mundo del piso, y = 0.002), solo delante de la cámara.
 * No se usa gridHelper porque sus líneas cruzan por detrás de la cámara y no se dibujaban.
 * Tras calibrar, 1 m real = scale_k unidades de la escena.
 */
export default function FloorGrid({ halfWidth = 8, depth = 14, near = 0.3 }) {
  const step = useStudio((s) => s.scaleK)
  const geometry = useMemo(() => {
    const pts: number[] = []
    const y = 0.002
    const n = Math.ceil(halfWidth / step)
    for (let i = -n; i <= n; i++) pts.push(i * step, y, -near, i * step, y, -depth)
    for (let z = -step; z >= -depth; z -= step) pts.push(-halfWidth, y, z, halfWidth, y, z)
    const g = new BufferGeometry()
    g.setAttribute('position', new Float32BufferAttribute(pts, 3))
    return g
  }, [halfWidth, depth, near, step])
  return (
    <lineSegments ref={markHelper} geometry={geometry} renderOrder={1}>
      <lineBasicMaterial color="#ffffff" transparent opacity={0.6} depthWrite={false} />
    </lineSegments>
  )
}
