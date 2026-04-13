import { useRef, useState, useCallback, createContext, useContext } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'

const PRESETS = {
  Top:       { position: [50, 120, 50],  target: [50, 0, 50] },
  Side:      { position: [120, 40, 50],  target: [50, 0, 50] },
  Cinematic: { position: [20, 60, 120],  target: [50, 0, 50] },
}

/**
 * Inner component that lives inside the R3F Canvas.
 * Handles OrbitControls and camera lerp animation.
 */
export function CameraControls({ preset }) {
  const controlsRef = useRef()
  const { camera } = useThree()

  const [targetPos, setTargetPos] = useState(null)
  const [targetLookAt, setTargetLookAt] = useState(null)
  const prevPreset = useRef(null)

  // Detect preset changes
  useFrame(() => {
    if (preset && preset !== prevPreset.current) {
      const p = PRESETS[preset]
      if (p) {
        setTargetPos(new THREE.Vector3(...p.position))
        setTargetLookAt(new THREE.Vector3(...p.target))
      }
      prevPreset.current = preset
    }

    if (!targetPos || !targetLookAt) return

    // Lerp camera position
    camera.position.lerp(targetPos, 0.05)

    // Lerp orbit controls target
    if (controlsRef.current) {
      controlsRef.current.target.lerp(targetLookAt, 0.05)
      controlsRef.current.update()
    }

    // Stop animating when close enough
    if (camera.position.distanceTo(targetPos) < 0.5) {
      setTargetPos(null)
      setTargetLookAt(null)
    }
  })

  return (
    <OrbitControls
      ref={controlsRef}
      target={[50, 0, 50]}
      enableDamping
      dampingFactor={0.1}
      minDistance={10}
      maxDistance={200}
    />
  )
}

/**
 * Preset buttons rendered as a fixed HTML overlay (outside of Canvas).
 */
export function CameraPresetButtons({ onPreset }) {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        gap: '12px',
        zIndex: 100,
      }}
    >
      {Object.keys(PRESETS).map((name) => (
        <button
          key={name}
          onClick={() => onPreset(name)}
          style={{
            padding: '8px 20px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.15)',
            background: 'rgba(255,255,255,0.08)',
            backdropFilter: 'blur(12px)',
            color: '#e0e0e0',
            fontSize: '13px',
            fontFamily: "'Inter', sans-serif",
            fontWeight: 500,
            cursor: 'pointer',
            letterSpacing: '0.5px',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.background = 'rgba(255,255,255,0.18)'
            e.target.style.borderColor = 'rgba(255,255,255,0.3)'
          }}
          onMouseLeave={(e) => {
            e.target.style.background = 'rgba(255,255,255,0.08)'
            e.target.style.borderColor = 'rgba(255,255,255,0.15)'
          }}
        >
          {name}
        </button>
      ))}
    </div>
  )
}
