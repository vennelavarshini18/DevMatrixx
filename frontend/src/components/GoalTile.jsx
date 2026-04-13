import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'

const SCALE = 100 / 15

export default function GoalTile({ x, y }) {
  const scanRingRef = useRef()
  const scanMatRef = useRef()
  const markerRefs = useRef([])

  useFrame(({ clock }) => {
    const t = clock.elapsedTime

    // Scan ring rises from 0.5 to 3 and resets every 2 seconds
    if (scanRingRef.current && scanMatRef.current) {
      const cycle = (t % 2) / 2 // 0 → 1 over 2 seconds
      scanRingRef.current.position.y = 0.5 + cycle * 2.5
      scanMatRef.current.opacity = 1 - cycle // fade out as it rises
    }

    // Corner marker pulse
    markerRefs.current.forEach((ref) => {
      if (ref) {
        ref.material.emissiveIntensity = 1 + Math.sin(t * 2) * 0.5
      }
    })
  })

  const px = x * SCALE
  const pz = y * SCALE

  return (
    <group position={[px, 0, pz]}>
      {/* ── Ground projection (faint glow) ── */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <circleGeometry args={[5, 24]} />
        <meshStandardMaterial
          color="#002200"
          emissive="#00FF00"
          emissiveIntensity={0.15}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* ── Base octagonal pad ── */}
      <mesh position={[0, 0.15, 0]}>
        <cylinderGeometry args={[4, 4, 0.3, 8]} />
        <meshStandardMaterial
          color="#1a3a1a"
          emissive="#00FF00"
          emissiveIntensity={0.3}
          roughness={0.6}
          metalness={0.3}
        />
      </mesh>

      {/* ── Corner markers (4 cardinal directions) ── */}
      {[
        [0, 0, 3.5],
        [0, 0, -3.5],
        [3.5, 0, 0],
        [-3.5, 0, 0],
      ].map((pos, i) => (
        <mesh
          key={`marker-${i}`}
          ref={(el) => (markerRefs.current[i] = el)}
          position={[pos[0], 1.8, pos[2]]}
        >
          <boxGeometry args={[0.4, 3, 0.4]} />
          <meshStandardMaterial
            color="#00FF00"
            emissive="#00FF00"
            emissiveIntensity={1}
          />
        </mesh>
      ))}

      {/* ── Landing arrows (pointing inward) ── */}
      {[
        { pos: [0, 0.4, 2.5], rot: [Math.PI / 2, 0, 0] },
        { pos: [0, 0.4, -2.5], rot: [-Math.PI / 2, 0, 0] },
        { pos: [2.5, 0.4, 0], rot: [0, 0, -Math.PI / 2] },
        { pos: [-2.5, 0.4, 0], rot: [0, 0, Math.PI / 2] },
      ].map((arrow, i) => (
        <mesh key={`arrow-${i}`} position={arrow.pos} rotation={arrow.rot}>
          <coneGeometry args={[0.6, 1.2, 4]} />
          <meshStandardMaterial
            color="#00FF44"
            emissive="#00FF44"
            emissiveIntensity={1}
          />
        </mesh>
      ))}

      {/* ── Scan ring (rises and fades) ── */}
      <mesh ref={scanRingRef} position={[0, 0.5, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[3.5, 0.15, 6, 24]} />
        <meshStandardMaterial
          ref={scanMatRef}
          color="#00FFAA"
          emissive="#00FFAA"
          emissiveIntensity={1.5}
          transparent
          opacity={1}
        />
      </mesh>

      {/* ── Center glow light ── */}
      <pointLight
        position={[0, 1, 0]}
        color="#00FF00"
        intensity={3}
        distance={10}
      />
    </group>
  )
}
