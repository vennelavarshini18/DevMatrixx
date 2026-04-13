import { useMemo } from 'react'
import * as THREE from 'three'

const SCALE = 100 / 15

export default function Floor() {
  // Create dashed lane texture for warehouse floor markings
  const lanePositions = useMemo(() => {
    const lanes = []
    // Horizontal warehouse aisles (every 3 logical cells)
    for (let i = 0; i <= 15; i += 3) {
      lanes.push({ axis: 'x', pos: i * SCALE })
    }
    // Vertical warehouse aisles
    for (let i = 0; i <= 15; i += 3) {
      lanes.push({ axis: 'z', pos: i * SCALE })
    }
    return lanes
  }, [])

  return (
    <group position={[0, 0, 0]}>
      {/* ── Main concrete floor ── */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[50, -0.05, 50]}>
        <planeGeometry args={[100, 100]} />
        <meshStandardMaterial color="#1c1c2a" roughness={0.9} metalness={0.05} />
      </mesh>

      {/* ── Subtle grid lines — structural floor grid ── */}
      <gridHelper
        args={[100, 15, '#2a2a3e', '#222235']}
        position={[50, 0, 50]}
      />

      {/* ── Yellow lane markings — warehouse aisles ── */}
      {lanePositions.map((lane, i) => {
        const isMainAisle = lane.pos === 0 || lane.pos === 100
        const color = isMainAisle ? '#f59e0b' : '#4a4520'
        const width = isMainAisle ? 0.3 : 0.15
        const opacity = isMainAisle ? 0.7 : 0.3

        if (lane.axis === 'x') {
          return (
            <mesh
              key={`lane-x-${i}`}
              rotation={[-Math.PI / 2, 0, 0]}
              position={[50, 0.02, lane.pos]}
            >
              <planeGeometry args={[100, width]} />
              <meshStandardMaterial
                color={color}
                transparent
                opacity={opacity}
                roughness={0.7}
              />
            </mesh>
          )
        } else {
          return (
            <mesh
              key={`lane-z-${i}`}
              rotation={[-Math.PI / 2, 0, 0]}
              position={[lane.pos, 0.02, 50]}
            >
              <planeGeometry args={[width, 100]} />
              <meshStandardMaterial
                color={color}
                transparent
                opacity={opacity}
                roughness={0.7}
              />
            </mesh>
          )
        }
      })}

      {/* ── Perimeter boundary — safety markings ── */}
      {/* Top edge */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[50, 0.03, 0]}>
        <planeGeometry args={[100, 0.6]} />
        <meshStandardMaterial color="#f59e0b" transparent opacity={0.6} />
      </mesh>
      {/* Bottom edge */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[50, 0.03, 100]}>
        <planeGeometry args={[100, 0.6]} />
        <meshStandardMaterial color="#f59e0b" transparent opacity={0.6} />
      </mesh>
      {/* Left edge */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 50]}>
        <planeGeometry args={[0.6, 100]} />
        <meshStandardMaterial color="#f59e0b" transparent opacity={0.6} />
      </mesh>
      {/* Right edge */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[100, 0.03, 50]}>
        <planeGeometry args={[0.6, 100]} />
        <meshStandardMaterial color="#f59e0b" transparent opacity={0.6} />
      </mesh>

      {/* ── Loading dock zones (corner accents) ── */}
      {[
        [5, 5],
        [95, 5],
        [5, 95],
        [95, 95],
      ].map(([lx, lz], i) => (
        <mesh
          key={`dock-${i}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[lx, 0.01, lz]}
        >
          <planeGeometry args={[8, 8]} />
          <meshStandardMaterial
            color="#1e3a5f"
            transparent
            opacity={0.25}
            roughness={0.8}
          />
        </mesh>
      ))}

      {/* ── Warehouse ambient — subtle overhead area lights ── */}
      <pointLight position={[25, 20, 25]} intensity={0.15} color="#ffeedd" distance={60} />
      <pointLight position={[75, 20, 25]} intensity={0.15} color="#ffeedd" distance={60} />
      <pointLight position={[25, 20, 75]} intensity={0.15} color="#ffeedd" distance={60} />
      <pointLight position={[75, 20, 75]} intensity={0.15} color="#ffeedd" distance={60} />
    </group>
  )
}
