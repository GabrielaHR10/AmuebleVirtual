import { Suspense, useLayoutEffect } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import { Box3, PerspectiveCamera, Sphere, Vector3 } from 'three'

// Página interna para generar miniaturas con Playwright: /thumb?glb=<url>&yaw=<grados>&view=front|right|left
declare global {
  interface Window {
    __thumbReady?: boolean
  }
}

function Model({ url, dir, yaw }: { url: string; dir: Vector3; yaw: number }) {
  const { scene } = useGLTF(url)
  const camera = useThree((s) => s.camera) as PerspectiveCamera
  const invalidate = useThree((s) => s.invalidate)

  useLayoutEffect(() => {
    scene.rotation.y = (yaw * Math.PI) / 180
    scene.updateMatrixWorld(true)
    const sphere = new Box3().setFromObject(scene).getBoundingSphere(new Sphere())
    const dist = (sphere.radius * 1.1) / Math.sin((camera.fov * Math.PI) / 360)
    camera.position.copy(sphere.center).addScaledVector(dir.clone().normalize(), dist)
    camera.near = dist / 100
    camera.far = dist * 10
    camera.lookAt(sphere.center)
    camera.updateProjectionMatrix()
    invalidate()
    const id = requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        window.__thumbReady = true
      }),
    )
    return () => cancelAnimationFrame(id)
  }, [scene, camera, dir, yaw, invalidate])

  return <primitive object={scene} />
}

export default function ThumbView() {
  useLayoutEffect(() => {
    document.body.style.background = 'transparent' // la miniatura debe quedar con fondo transparente
  }, [])
  const params = new URLSearchParams(window.location.search)
  const url = params.get('glb') ?? ''
  const views: Record<string, Vector3> = {
    front: new Vector3(0, 0.15, 1),
    right: new Vector3(1, 0.15, 0),
    left: new Vector3(-1, 0.15, 0),
  }
  const dir = views[params.get('view') ?? ''] ?? new Vector3(0.75, 0.5, 1)
  return (
    <div style={{ width: 512, height: 512 }}>
      <Canvas gl={{ preserveDrawingBuffer: true, alpha: true, antialias: true }} camera={{ fov: 30 }}>
        <hemisphereLight args={['#ffffff', '#b9a58c', 1.4]} />
        <directionalLight position={[3, 5, 4]} intensity={2.2} />
        <Suspense fallback={null}>
          <Model url={url} dir={dir} yaw={Number(params.get('yaw') ?? 0)} />
        </Suspense>
      </Canvas>
    </div>
  )
}
