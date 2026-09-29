import { createElement, useEffect, useLayoutEffect, useRef, type ReactNode } from 'react'
import { useThree } from '@react-three/fiber'
import {
  Color,
  Group,
  Mesh,
  MeshBasicMaterial,
  ShaderMaterial,
  type Camera,
  type Material,
  type Object3D,
  type PerspectiveCamera,
  type Scene as ThreeScene,
  type Texture,
  type WebGLRenderer,
  Vector2,
} from 'three'

// Capa de "ayudas" (cuadrícula, huellas, marcadores): se ve en el editor pero no en la exportación.
export const HELPER_LAYER = 1

export function markHelper(o: Object3D | null) {
  o?.traverse((c) => c.layers.set(HELPER_LAYER))
}

/** Grupo cuyos hijos (aunque cambien) quedan en la capa de ayudas. */
export function HelperGroup({ children }: { children: ReactNode }) {
  const ref = useRef<Group>(null)
  useLayoutEffect(() => markHelper(ref.current))
  return createElement('group', { ref }, children)
}

interface Exporter {
  gl: WebGLRenderer
  scene: ThreeScene
  camera: PerspectiveCamera
}

let current: Exporter | null = null

/** Componente dentro del <Canvas> que deja disponible el renderer para exportar. */
export function ExportBridge() {
  const { gl, scene, camera } = useThree()
  useEffect(() => {
    camera.layers.enable(HELPER_LAYER)
    current = { gl, scene, camera: camera as PerspectiveCamera }
    return () => {
      current = null
    }
  }, [gl, scene, camera])
  return null
}

/** Renderiza la escena 3D a W×H sin ayudas; `prepare` puede cambiar la escena y devuelve cómo deshacerlo. */
function renderAt(width: number, height: number, prepare?: (s: ThreeScene, gl: WebGLRenderer) => () => void) {
  if (!current) throw new Error('El editor no está listo')
  const { gl, scene, camera } = current
  const size = gl.getSize(new Vector2())
  const ratio = gl.getPixelRatio()
  const aspect = camera.aspect
  camera.layers.disable(HELPER_LAYER)
  gl.setPixelRatio(1)
  gl.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  // los fantasmas (sugerencias sin aceptar) nunca se exportan
  const ghosts: Object3D[] = []
  scene.traverse((o) => {
    if (o.userData.ghost && o.visible) {
      ghosts.push(o)
      o.visible = false
    }
  })
  const undo = prepare?.(scene, gl)
  const out = document.createElement('canvas')
  out.width = width
  out.height = height
  try {
    gl.render(scene, camera as Camera)
    out.getContext('2d')!.drawImage(gl.domElement, 0, 0, width, height)
  } finally {
    undo?.()
    ghosts.forEach((o) => (o.visible = true))
    camera.layers.enable(HELPER_LAYER)
    gl.setPixelRatio(ratio)
    gl.setSize(size.x, size.y, false)
    camera.aspect = aspect
    camera.updateProjectionMatrix()
    gl.render(scene, camera as Camera)
  }
  return out
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('No se pudo cargar la foto'))
    img.src = url
  })
}

function toBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('No se pudo crear el PNG'))), 'image/png'),
  )
}

/** Foto + muebles (con sombras) al tamaño natural de la foto (PLAN 2.10). */
export async function exportComposite(photoUrl: string, width: number, height: number): Promise<Blob> {
  const photo = await loadImage(photoUrl)
  const three = renderAt(width, height)
  const out = document.createElement('canvas')
  out.width = width
  out.height = height
  const g = out.getContext('2d')!
  g.drawImage(photo, 0, 0, width, height)
  g.drawImage(three, 0, 0)
  return toBlob(out)
}

const cutoutMaskMaterial = (map: Texture | null) =>
  new ShaderMaterial({
    uniforms: { map: { value: map } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader:
      'uniform sampler2D map; varying vec2 vUv; void main() { if (texture2D(map, vUv).a < 0.5) discard; gl_FragColor = vec4(1.0); }',
  })

/** Máscara de muebles: blanco sobre negro, mismo tamaño (para el retoque IA de la Fase 4). */
export async function exportFurnitureMask(width: number, height: number): Promise<Blob> {
  const canvas = renderAt(width, height, (scene, gl) => {
    const swaps: [Mesh, Material | Material[]][] = []
    const hidden: Object3D[] = []
    const white = new MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
    scene.traverse((o) => {
      if (o.userData.noMask && o.visible) {
        hidden.push(o)
        o.visible = false
      }
    })
    scene.traverse((o) => {
      if (!(o instanceof Mesh) || !isFurniture(o)) return
      swaps.push([o, o.material])
      const m = o.material as MeshBasicMaterial
      o.material = m.map && m.transparent ? cutoutMaskMaterial(m.map) : white
    })
    const prevColor = gl.getClearColor(new Color())
    const prevAlpha = gl.getClearAlpha()
    const prevBg = scene.background
    const prevEnv = scene.environment
    scene.background = new Color(0x000000)
    scene.environment = null
    gl.setClearColor(0x000000, 1)
    return () => {
      swaps.forEach(([o, mat]) => (o.material = mat))
      hidden.forEach((o) => (o.visible = true))
      scene.background = prevBg
      scene.environment = prevEnv
      gl.setClearColor(prevColor, prevAlpha)
    }
  })
  return toBlob(canvas)
}

function isFurniture(o: Object3D): boolean {
  for (let p: Object3D | null = o; p; p = p.parent) if (p.userData.furniture) return true
  return false
}

export function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

export function exportFileName(prefix = 'amoblado'): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${prefix}_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}.png`
}
