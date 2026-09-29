import { Matrix4, Vector3 } from 'three'

// Misma convención que backend/app/geometry/coords.py (PLAN §4): todo en coords three.

export type Vec2 = [number, number]

/** Marco del piso (columnas x, y, z, origen) desde el plano n·p + d = 0 con n hacia la cámara. */
export function floorFrameFromPlane(normal: Vector3, d: number): Matrix4 {
  let n = normal.clone().normalize()
  if (d < 0) {
    n = n.negate()
    d = -d
  }
  const forward = new Vector3(0, 0, -1)
  const f = forward.clone().sub(n.clone().multiplyScalar(forward.dot(n)))
  if (f.length() < 1e-6) throw new Error('La cámara mira perpendicular al piso')
  f.normalize()
  const yAxis = n
  const zAxis = f.clone().negate()
  const xAxis = new Vector3().crossVectors(yAxis, zAxis)
  const origin = n.clone().multiplyScalar(-d)
  return new Matrix4().makeBasis(xAxis, yAxis, zAxis).setPosition(origin)
}

/** Plano (n, d) que pasa por 3 puntos, con n hacia la cámara (origen). */
export function planeFromPoints(a: Vector3, b: Vector3, c: Vector3): { normal: Vector3; d: number } {
  const n = new Vector3().crossVectors(b.clone().sub(a), c.clone().sub(a)).normalize()
  let d = -n.dot(a)
  if (d < 0) {
    n.negate()
    d = -d
  }
  return { normal: n, d }
}

/** Punto del piso (mundo del piso) → píxel normalizado [0..1] de la foto. null si queda detrás de la cámara. */
export function projectFloorPoint(
  p: Vector3,
  frame: Matrix4,
  cameraWorld: Matrix4,
  intrinsics: number[][],
): Vec2 | null {
  const cam = p.clone().applyMatrix4(frame).applyMatrix4(cameraWorld.clone().invert())
  const depth = -cam.z
  if (depth <= 1e-3) return null
  const u = 0.5 + (intrinsics[0][0] * cam.x) / depth
  const v = 0.5 - (intrinsics[1][1] * cam.y) / depth
  return [u, v]
}

/** Esquinas (x, z) de la huella width × depth centrada en (x, z) y girada yaw grados. */
export function footprintCorners(x: number, z: number, width: number, depth: number, yawDeg: number): Vec2[] {
  const a = (yawDeg * Math.PI) / 180
  const c = Math.cos(a)
  const s = Math.sin(a)
  const hw = width / 2
  const hd = depth / 2
  return [
    [-hw, -hd],
    [hw, -hd],
    [hw, hd],
    [-hw, hd],
  ].map(([lx, lz]) => [x + lx * c + lz * s, z - lx * s + lz * c] as Vec2)
}

/** ¿Se cruzan dos polígonos convexos? (teorema del eje separador) */
export function polygonsOverlap(a: Vec2[], b: Vec2[]): boolean {
  for (const poly of [a, b]) {
    for (let i = 0; i < poly.length; i++) {
      const [x1, z1] = poly[i]
      const [x2, z2] = poly[(i + 1) % poly.length]
      const axis: Vec2 = [z2 - z1, x1 - x2]
      const proj = (p: Vec2[]) => p.map(([x, z]) => x * axis[0] + z * axis[1])
      const pa = proj(a)
      const pb = proj(b)
      if (Math.max(...pa) <= Math.min(...pb) + 1e-9 || Math.max(...pb) <= Math.min(...pa) + 1e-9) return false
    }
  }
  return true
}

/**
 * Punto del piso bajo el centro de la imagen (mundo del piso). Si el rayo no toca el piso
 * o cae a más de 8 m, se usa un punto 3 m delante de la cámara.
 */
export function dropPoint(frame: Matrix4, cameraWorld: Matrix4): Vector3 {
  const toFloor = frame.clone().invert().multiply(cameraWorld)
  const origin = new Vector3().applyMatrix4(toFloor)
  const dir = new Vector3(0, 0, -1).transformDirection(toFloor)
  if (dir.y < -1e-3) {
    const t = -origin.y / dir.y
    const hit = origin.clone().addScaledVector(dir, t)
    if (hit.distanceTo(new Vector3(origin.x, 0, origin.z)) <= 8) return hit.setY(0)
  }
  const flat = new Vector3(dir.x, 0, dir.z)
  if (flat.lengthSq() < 1e-9) flat.set(0, 0, -1)
  return new Vector3(origin.x, 0, origin.z).addScaledVector(flat.normalize(), 3)
}
