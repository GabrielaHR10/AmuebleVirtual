import type { Scene } from '../api/client'

// Luz que imita la de la foto (PLAN 4.1): color/brillo del piso y dirección desde la ventana.

export interface LightSettings {
  hemiColor: string
  hemiIntensity: number
  azimuth: number // grados, de dónde viene la luz (mundo del piso: 0 = desde el fondo del cuarto, −z)
  elevation: number // grados sobre el horizonte
  exposure: number
}

export const DEFAULT_LIGHT: LightSettings = {
  hemiColor: '#ffffff',
  hemiIntensity: 0.8,
  azimuth: 180, // desde arriba y atrás de la cámara
  elevation: 45,
  exposure: 1,
}

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))

export function autoLight(scene: Scene, center: [number, number, number]): LightSettings {
  const l = scene.lighting
  if (!l) return DEFAULT_LIGHT
  let hemiColor = DEFAULT_LIGHT.hemiColor
  if (l.floor_rgb) {
    const max = Math.max(...l.floor_rgb, 1)
    // tono del piso (normalizado) mezclado 60 % con blanco: luz cálida o fría según la foto
    const c = l.floor_rgb.map((v) => Math.round(255 * (0.6 + 0.4 * (v / max))))
    hemiColor = `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`
  }
  const lum = l.floor_luminance ?? 0.18
  const hemiIntensity = clamp(0.5 + 0.7 * (lum / 0.25), 0.5, 1.2)
  const exposure = clamp(0.8 + 1.2 * (lum - 0.18), 0.7, 1.2)
  let azimuth = DEFAULT_LIGHT.azimuth
  if (l.light_source) {
    const [sx, , sz] = l.light_source
    azimuth = (Math.atan2(sx - center[0], -(sz - center[2])) * 180) / Math.PI
    azimuth = (azimuth + 360) % 360
  }
  return { hemiColor, hemiIntensity, azimuth, elevation: 40, exposure }
}

/** Posición de la luz direccional (mundo del piso) respecto al centro de los muebles. */
export function lightPosition(s: LightSettings, center: [number, number, number], dist = 6): [number, number, number] {
  const az = (s.azimuth * Math.PI) / 180
  const el = (s.elevation * Math.PI) / 180
  return [
    center[0] + Math.sin(az) * Math.cos(el) * dist,
    Math.sin(el) * dist,
    center[2] - Math.cos(az) * Math.cos(el) * dist,
  ]
}
