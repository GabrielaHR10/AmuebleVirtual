import { useLayoutEffect, useRef, useState } from 'react'
import { Object3D, type DirectionalLight } from 'three'
import { lightPosition, type LightSettings } from './lighting'

/** Luces del grupo del piso (editor y render de video): la direccional apunta al centro de los muebles. */
export default function FloorLights({ target, settings }: { target: [number, number, number]; settings: LightSettings }) {
  const light = useRef<DirectionalLight>(null)
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
