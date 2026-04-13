import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const SCALE = 100 / 15

const STATUS_COLORS = {
  moving:       { color: '#00BFFF', emissive: '#003366', light: '#00FFFF' },
  collided:     { color: '#FF0000', emissive: '#330000', light: '#FF0000' },
  reached_goal: { color: '#00FF00', emissive: '#003300', light: '#00FF00' },
}

export default function Agent({ x, y, status }) {
  const groupRef = useRef()
  const domeRef = useRef()
  const currentPos = useRef(new THREE.Vector3(x * SCALE, 0, y * SCALE))
  const prevPos = useRef(new THREE.Vector3(x * SCALE, 0, y * SCALE))
  const currentAngle = useRef(0)

  const targetPos = useMemo(
    () => new THREE.Vector3(x * SCALE, 0, y * SCALE),
    [x, y]
  )

  const colors = STATUS_COLORS[status] || STATUS_COLORS.moving

  useFrame(({ clock }) => {
    if (!groupRef.current) return

    const oldX = currentPos.current.x
    const oldZ = currentPos.current.z

    currentPos.current.lerp(targetPos, 0.15)
    groupRef.current.position.copy(currentPos.current)

    const dx = currentPos.current.x - oldX
    const dz = currentPos.current.z - oldZ
    if (Math.abs(dx) > 0.001 || Math.abs(dz) > 0.001) {
      const targetAngle = Math.atan2(dx, dz)
      currentAngle.current += (targetAngle - currentAngle.current) * 0.1
      groupRef.current.rotation.y = currentAngle.current

     
      groupRef.current.rotation.x = -0.08
    } else {
      groupRef.current.rotation.x *= 0.95
    }

    
    if (domeRef.current) {
      domeRef.current.rotation.y += 0.02
    }

    prevPos.current.copy(currentPos.current)
  })

  const t = 0 

  return (
    <group ref={groupRef} position={[x * SCALE, 0, y * SCALE]}>
      {/* ── BASE CHASSIS ── */}
      <mesh position={[0, 1.2, 0]} castShadow receiveShadow>
        <boxGeometry args={[4, 2, 4]} />
        <meshStandardMaterial
          color={colors.color}
          roughness={0.2}
          metalness={0.8}
          emissive={colors.emissive}
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* ── SENSOR DOME ── */}
      <group ref={domeRef} position={[0, 3, 0]}>
        <mesh>
          <sphereGeometry args={[1.2, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial
            color="#111111"
            roughness={0.1}
            metalness={0.9}
          />
        </mesh>

        {/* Scanning rings */}
        <ScanRing radius={1.3} tilt={0.2} color={colors.light} />
        <ScanRing radius={1.6} tilt={-0.15} color={colors.light} />
        <ScanRing radius={1.9} tilt={0.3} color={colors.light} />
      </group>

      {/* ── TREADS (4 corners) ── */}
      {[
        [-1.8, 0.75, -1.6],
        [1.8, 0.75, -1.6],
        [-1.8, 0.75, 1.6],
        [1.8, 0.75, 1.6],
      ].map((pos, i) => (
        <group key={`tread-${i}`} position={pos}>
          <mesh castShadow>
            <boxGeometry args={[1.2, 1.5, 3]} />
            <meshStandardMaterial color="#222" roughness={0.8} metalness={0.3} />
          </mesh>
          {/* Tread lines */}
          {[-1, -0.5, 0, 0.5, 1].map((tz, ti) => (
            <mesh key={`tl-${ti}`} position={[0.61 * (i % 2 === 0 ? -1 : 1), 0, tz * 0.9]}>
              <boxGeometry args={[0.05, 1.3, 0.15]} />
              <meshStandardMaterial color="#333" />
            </mesh>
          ))}
        </group>
      ))}

      {/* ── STATUS LIGHT STRIPS (front) ── */}
      <mesh position={[0, 1.5, 2.05]}>
        <boxGeometry args={[3, 0.4, 0.1]} />
        <meshStandardMaterial
          color={colors.light}
          emissive={colors.light}
          emissiveIntensity={2}
        />
      </mesh>
      <mesh position={[0, 0.8, 2.05]}>
        <boxGeometry args={[3, 0.3, 0.1]} />
        <meshStandardMaterial
          color={colors.light}
          emissive={colors.light}
          emissiveIntensity={1.5}
        />
      </mesh>

      {/* ── Underside glow ── */}
      <pointLight
        position={[0, 0.3, 0]}
        color={colors.light}
        intensity={2}
        distance={8}
      />
    </group>
  )
}

/* ── Animated scan ring ── */
function ScanRing({ radius, tilt, color }) {
  const ref = useRef()

  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.material.emissiveIntensity = 1 + Math.sin(clock.elapsedTime * 3) * 0.5
    }
  })

  return (
    <mesh ref={ref} rotation={[tilt, 0, 0]} position={[0, 0.2, 0]}>
      <torusGeometry args={[radius, 0.05, 6, 24]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={1.5}
        transparent
        opacity={0.7}
      />
    </mesh>
  )
}
