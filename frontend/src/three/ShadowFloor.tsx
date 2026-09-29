// Piso invisible que solo recibe sombras (dentro del grupo del piso, y = 0.001).
export default function ShadowFloor({ opacity = 0.3 }: { opacity?: number }) {
  return (
    <mesh rotation-x={-Math.PI / 2} position-y={0.001} receiveShadow>
      <planeGeometry args={[30, 30]} />
      <shadowMaterial transparent opacity={opacity} depthWrite={false} />
    </mesh>
  )
}
