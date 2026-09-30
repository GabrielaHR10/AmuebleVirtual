import { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Canvas, useThree, type ThreeEvent } from '@react-three/fiber'
import { SoftShadows } from '@react-three/drei'
import { Matrix4, Object3D, PerspectiveCamera, type DirectionalLight } from 'three'
import type { Scene } from '../api/client'
import { useStudio, type Toggles } from '../store/useStudio'
import { dropPoint } from './math'
import { ExportBridge, HelperGroup } from './exportImage'
import FloorGrid from './FloorGrid'
import { autoLight, lightPosition } from './lighting'
import OcclusionMesh from './OcclusionMesh'
import PhotoEnvironment from './PhotoEnvironment'
import ShadowFloor from './ShadowFloor'

/** Cámara fija a la foto: mismo FOV y pose (identidad en fotos; la Fase 5 usará otras poses). */
function SceneCamera({ scene }: { scene: Scene }) {
  const camera = useThree((s) => s.camera) as PerspectiveCamera
  useLayoutEffect(() => {
    camera.fov = scene.camera.fov_y_deg
    camera.near = 0.05
    camera.far = 100
    new Matrix4().fromArray(scene.camera.matrix_world).decompose(camera.position, camera.quaternion, camera.scale)
    camera.updateProjectionMatrix()
  }, [camera, scene])
  return null
}

/** Exposición de los muebles 3D (los recortes la aplican en su material). */
function Exposure() {
  const gl = useThree((s) => s.gl)
  const exposure = useStudio((s) => s.light.exposure)
  useLayoutEffect(() => {
    gl.toneMappingExposure = exposure
  }, [gl, exposure])
  return null
}

/** Luces del grupo del piso: la direccional apunta al centro del piso visible. */
function FloorLights({ target }: { target: [number, number, number] }) {
  const light = useRef<DirectionalLight>(null)
  const settings = useStudio((s) => s.light)
  const [targetObj] = useState(() => new Object3D())
  useLayoutEffect(() => {
    targetObj.position.set(...target)
    if (light.current) light.current.target = targetObj
  }, [target, targetObj])
  return (
    <>
      <primitive object={targetObj} />
      <hemisphereLight args={[settings.hemiColor, '#8d7b68', settings.hemiIntensity]} />
      <directionalLight
        ref={light}
        position={lightPosition(settings, target)}
        intensity={1.6}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-6}
        shadow-camera-right={6}
        shadow-camera-top={6}
        shadow-camera-bottom={-6}
        shadow-camera-near={0.5}
        shadow-camera-far={20}
        shadow-bias={-0.0005}
      />
    </>
  )
}

/** Puntos marcados para el piso manual (coords de cámara/mundo, fuera del grupo del piso). */
function ManualFloorMarks() {
  const manual = useStudio((s) => s.manualFloor)
  if (!manual.active) return null
  return (
    <HelperGroup>
      {manual.points.map((p, i) => (
        <mesh key={i} position={p} renderOrder={5}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshBasicMaterial color="#f59e0b" depthTest={false} />
        </mesh>
      ))}
    </HelperGroup>
  )
}

/** Tamaño en pantalla de la foto dentro del contenedor, conservando su proporción (letterbox). */
function useLetterbox(aspect: number) {
  const ref = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState({ width: 0, height: 0 })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => {
      const { clientWidth: w, clientHeight: h } = el
      setBox(w / h > aspect ? { width: h * aspect, height: h } : { width: w, height: w / aspect })
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [aspect])
  return { ref, box }
}

interface Props {
  scene: Scene
  toggles: Toggles
  children?: ReactNode // muebles: van DENTRO del grupo del piso
  onFloorPointerMissed?: () => void
}

export default function Editor3D({ scene, toggles, children, onFloorPointerMissed }: Props) {
  const aspect = scene.image.width / scene.image.height
  const { ref, box } = useLetterbox(aspect)
  const frame = useMemo(() => (scene.floor.frame ? new Matrix4().fromArray(scene.floor.frame) : null), [scene])
  const center = useMemo<[number, number, number]>(() => {
    if (!frame) return [0, 0, -3]
    const p = dropPoint(frame, new Matrix4().fromArray(scene.camera.matrix_world))
    return [p.x, 0, p.z]
  }, [frame, scene])
  const maskUrl = scene.assets.floor_mask_png
  const setLight = useStudio((s) => s.setLight)
  useEffect(() => setLight(autoLight(scene, center)), [scene, center, setLight]) // ajuste automático de luz
  const manualActive = useStudio((s) => s.manualFloor.active)
  const onPick = (e: ThreeEvent<MouseEvent>) => {
    const { manualFloor, setManualFloor } = useStudio.getState()
    if (!manualFloor.active || manualFloor.points.length >= 3) return
    e.stopPropagation()
    const p = e.point
    setManualFloor({ active: true, points: [...manualFloor.points, [p.x, p.y, p.z]] })
  }

  return (
    <div ref={ref} className="relative flex h-full w-full items-center justify-center overflow-hidden bg-stone-900">
      <div data-testid="editor" className="relative" style={{ width: box.width, height: box.height }}>
        <img src={scene.image.url} alt="Foto del espacio" className="absolute inset-0 h-full w-full select-none" draggable={false} />
        {toggles.floorMask && maskUrl && (
          <div
            className="pointer-events-none absolute inset-0 bg-emerald-400/45"
            style={{ maskImage: `url(${maskUrl})`, maskSize: '100% 100%', maskMode: 'luminance' }}
          />
        )}
        {box.width > 0 && (
          <Canvas
            className="!absolute inset-0"
            shadows={toggles.shadows}
            gl={{ alpha: true, preserveDrawingBuffer: true, antialias: true }}
            onPointerMissed={onFloorPointerMissed}
          >
            {/* sombras de borde suave (PCSS): la luz de una ventana es difusa */}
            <SoftShadows size={5} samples={12} focus={0.3} />
            <SceneCamera scene={scene} />
            <ExportBridge />
            <Exposure />
            <ManualFloorMarks />
            <Suspense fallback={null}>
              <PhotoEnvironment scene={scene} />
              {/* Con piso manual la malla incluye el piso real y taparía los muebles: solo se usa para marcar */}
              {((toggles.occlusion && !scene.warnings.includes('piso_manual')) || manualActive) &&
                scene.assets.occlusion_glb && (
                <OcclusionMesh url={scene.assets.occlusion_glb} onPick={manualActive ? onPick : undefined} />
              )}
            </Suspense>
            {frame && (
              <group matrixAutoUpdate={false} matrix={frame}>
                <FloorLights target={center} />
                <ShadowFloor />
                {toggles.grid && <FloorGrid />}
                <Suspense fallback={null}>{children}</Suspense>
              </group>
            )}
          </Canvas>
        )}
      </div>
    </div>
  )
}
