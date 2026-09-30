import { Suspense, useEffect, useMemo, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { SoftShadows } from '@react-three/drei'
import { Matrix4, ShaderMaterial, type PerspectiveCamera } from 'three'
import type { CatalogItem, ClipTrack, Scene } from '../api/client'
import CutoutBillboard from './CutoutBillboard'
import FloorLights from './FloorLights'
import FurnitureModel from './FurnitureModel'
import { autoLight } from './lighting'
import { dropPoint } from './math'
import PhotoEnvironment from './PhotoEnvironment'
import ShadowFloor from './ShadowFloor'

// Render del video con muebles (R.5): por cada fotograma se fija la cámara del seguimiento y se sacan dos
// imágenes: los muebles (con sombras, fondo transparente) y su profundidad, que el servidor compara con la
// profundidad real del fotograma (MoGe) para que paredes y objetos tapen a los muebles.

export const DEPTH_FAR_M = 20

/** Profundidad (distancia a lo largo de la cámara) empaquetada en RGB, base 255 (ver backend clips.unpack_depth). */
const depthMaterial = new ShaderMaterial({
  vertexShader: `varying float vDepth;
    void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vDepth = -mv.z; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `varying float vDepth;
    void main() {
      float v = clamp(vDepth / ${DEPTH_FAR_M.toFixed(1)}, 0.0, 0.999999);
      vec3 enc = fract(vec3(1.0, 255.0, 65025.0) * v);
      enc.xy -= enc.yz / 255.0;
      gl_FragColor = vec4(enc, 1.0);
    }`,
})

const toBlob = (c: HTMLCanvasElement) =>
  new Promise<Blob>((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error('No se pudo crear el PNG'))), 'image/png'))

interface DriverProps {
  track: ClipTrack
  upload: (k: number, color: Blob, depth: Blob) => Promise<void>
  onProgress: (done: number, total: number) => void
  onDone: () => void
  onError: (e: unknown) => void
}

function Driver({ track, upload, onProgress, onDone, onError }: DriverProps) {
  const { gl, scene, camera, advance } = useThree()
  const started = useRef(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    const cam = camera as PerspectiveCamera
    const run = async () => {
      // el Driver está dentro del Suspense: al montarse ya cargaron modelos y texturas
      await new Promise((r) => setTimeout(r, 300))
      cam.fov = track.fov_y_deg
      cam.aspect = track.width / track.height
      cam.near = 0.05
      cam.far = 100
      cam.updateProjectionMatrix()
      cam.matrixAutoUpdate = false
      gl.setClearColor(0x000000, 0)
      for (const f of track.frames) {
        cam.matrix.fromArray(f.matrix_world)
        cam.matrix.decompose(cam.position, cam.quaternion, cam.scale)
        cam.updateMatrixWorld(true)
        advance(performance.now()) // useFrame (los recortes miran a la cámara) + render de color
        const color = await toBlob(gl.domElement)
        scene.overrideMaterial = depthMaterial
        gl.render(scene, cam)
        scene.overrideMaterial = null
        const depth = await toBlob(gl.domElement)
        await upload(f.i, color, depth)
        onProgress(f.i + 1, track.frames.length)
      }
      onDone()
    }
    run().catch(onError)
  }, [track, gl, scene, camera, advance, upload, onProgress, onDone, onError])
  return null
}

interface Props extends Omit<DriverProps, 'track'> {
  track: ClipTrack
  scene: Scene // escena del fotograma de referencia (piso y muebles)
  catalog: CatalogItem[]
}

/** Lienzo fuera de pantalla que renderiza y sube todos los fotogramas del tramo. */
export default function VideoRenderer({ track, scene, catalog, ...rest }: Props) {
  const frame = useMemo(() => new Matrix4().fromArray(scene.floor.frame!), [scene])
  const center = useMemo<[number, number, number]>(() => {
    const p = dropPoint(frame, new Matrix4())
    return [p.x, 0, p.z]
  }, [frame])
  const light = useMemo(() => autoLight(scene, center), [scene, center])
  const byId = new Map(catalog.map((i) => [i.id, i]))
  return (
    <div style={{ position: 'fixed', left: -100000, top: 0, width: track.width, height: track.height }}>
      <Canvas
        frameloop="never"
        shadows
        dpr={1}
        style={{ width: track.width, height: track.height }}
        gl={{ alpha: true, preserveDrawingBuffer: true, antialias: true, toneMappingExposure: light.exposure }}
      >
        <SoftShadows size={5} samples={12} focus={0.3} />
        <Suspense fallback={null}>
          <PhotoEnvironment scene={scene} />
          <group matrixAutoUpdate={false} matrix={frame}>
            <FloorLights target={center} settings={light} />
            <ShadowFloor />
            {scene.placements.map((p) => {
              const item = byId.get(p.item_id)
              if (!item) return null
              return (
                <group key={p.uid} position={[p.x, 0, p.z]} rotation-y={(p.yaw_deg * Math.PI) / 180}>
                  {p.mode === '3d' && item.glb_url ? (
                    <FurnitureModel item={item} scaleK={scene.scale_k} />
                  ) : (
                    <CutoutBillboard item={item} scaleK={scene.scale_k} />
                  )}
                </group>
              )
            })}
          </group>
          <Driver track={track} {...rest} />
        </Suspense>
      </Canvas>
    </div>
  )
}
