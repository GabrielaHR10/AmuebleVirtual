import { useStudio } from '../store/useStudio'

// Piso invisible que solo recibe sombras (dentro del grupo del piso, y = 0.001).
export default function ShadowFloor() {
  const opacity = useStudio((s) => s.shadowOpacity)
  return (
    <mesh rotation-x={-Math.PI / 2} position-y={0.001} receiveShadow userData={{ noMask: true }}>
      <planeGeometry args={[30, 30]} />
      <shadowMaterial transparent opacity={opacity} depthWrite={false} />
    </mesh>
  )
}
