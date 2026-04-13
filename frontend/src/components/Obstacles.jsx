import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const SCALE = 100 / 15
const CARDBOARD_COLORS = ['#C19A6B', '#A0785A', '#B8935A', '#D2A679']

/* ═══════════════════════════════════════════════════════════
   SHARED — Cardboard box with tape cross
   ═══════════════════════════════════════════════════════════ */
function CardboardBox({ position, size, color, rotation = [0, 0, 0] }) {
  return (
    <group position={position} rotation={rotation}>
      <mesh castShadow>
        <boxGeometry args={size} />
        <meshStandardMaterial color={color} roughness={0.95} metalness={0} />
      </mesh>
      {/* Tape cross on top */}
      <mesh position={[0, size[1] / 2 + 0.026, 0]}>
        <boxGeometry args={[size[0] * 0.8, 0.05, 0.15]} />
        <meshStandardMaterial color="#8B6914" roughness={0.8} />
      </mesh>
      <mesh position={[0, size[1] / 2 + 0.026, 0]}>
        <boxGeometry args={[0.15, 0.05, size[2] * 0.8]} />
        <meshStandardMaterial color="#8B6914" roughness={0.8} />
      </mesh>
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   STATIC → SHELF UNIT with cargo
   ═══════════════════════════════════════════════════════════ */
function ShelfUnit({ x, y }) {
  // Random but deterministic box colors based on position
  const boxColors = useMemo(() => {
    const seed = x * 17 + y * 31
    return Array.from({ length: 8 }, (_, i) =>
      CARDBOARD_COLORS[(seed + i) % CARDBOARD_COLORS.length]
    )
  }, [x, y])

  const hasTopBox = useMemo(() => (x + y) % 3 !== 0, [x, y])

  return (
    <group position={[x * SCALE, 0, y * SCALE]}>
      {/* ── UPRIGHTS (2 tall steel frames) ── */}
      {[-SCALE * 0.4, SCALE * 0.4].map((xo, i) => (
        <mesh
          key={`upright-${i}`}
          position={[xo, 5, 0]}
          castShadow
        >
          <boxGeometry args={[0.4, 10, 0.4]} />
          <meshStandardMaterial color="#8B8B8B" roughness={0.5} metalness={0.6} />
        </mesh>
      ))}

      {/* Back bracing (diagonal — simplified as vertical) */}
      <mesh position={[0, 5, -SCALE * 0.35]} castShadow>
        <boxGeometry args={[0.15, 10, 0.15]} />
        <meshStandardMaterial color="#7a7a7a" roughness={0.6} metalness={0.5} />
      </mesh>

      {/* ── SHELF BOARDS (3 levels) ── */}
      {[1, 4, 7.5].map((yLevel, i) => (
        <mesh
          key={`shelf-${i}`}
          position={[0, yLevel, 0]}
          castShadow
          receiveShadow
        >
          <boxGeometry args={[SCALE, 0.3, SCALE * 0.8]} />
          <meshStandardMaterial color="#6B6B6B" roughness={0.6} metalness={0.5} />
        </mesh>
      ))}

      {/* ── CARGO ON BOTTOM SHELF ── */}
      <CardboardBox
        position={[-1, 2.2, 0.2]}
        size={[1.8, 2, 1.8]}
        color={boxColors[0]}
      />
      <CardboardBox
        position={[1.2, 2, -0.1]}
        size={[1.6, 1.7, 1.6]}
        color={boxColors[1]}
      />

      {/* ── CARGO ON MIDDLE SHELF ── */}
      <CardboardBox
        position={[-1.3, 5.1, 0]}
        size={[1.3, 1.5, 1.4]}
        color={boxColors[2]}
      />
      <CardboardBox
        position={[0.2, 4.9, 0.3]}
        size={[1.5, 1.3, 1.3]}
        color={boxColors[3]}
      />
      <CardboardBox
        position={[1.5, 5.0, -0.2]}
        size={[1.2, 1.4, 1.2]}
        color={boxColors[4]}
      />

      {/* ── CARGO ON TOP SHELF (random) ── */}
      {hasTopBox && (
        <CardboardBox
          position={[0, 8.5, 0]}
          size={[2.2, 1.5, 2]}
          color={boxColors[5]}
        />
      )}
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   PATROL → FORKLIFT ROBOT
   ═══════════════════════════════════════════════════════════ */
function ForkLift({ x, y, dx = 0, dy = 0 }) {
  const groupRef = useRef()
  const currentPos = useRef(new THREE.Vector3(x * SCALE, 0, y * SCALE))
  const currentAngle = useRef(0)
  const wheelRot = useRef(0)
  const leftEyeRef = useRef()
  const rightEyeRef = useRef()

  const targetPos = useMemo(
    () => new THREE.Vector3(x * SCALE, 0, y * SCALE),
    [x, y]
  )

  const targetAngle = useMemo(() => {
    if (dx === 0 && dy === 0) return 0
    return Math.atan2(dx, dy)
  }, [dx, dy])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.elapsedTime

    // Lerp position (heavy vehicle feel)
    const prevX = currentPos.current.x
    const prevZ = currentPos.current.z
    currentPos.current.lerp(targetPos, 0.1)
    groupRef.current.position.copy(currentPos.current)

    // Rotate to face direction
    currentAngle.current += (targetAngle - currentAngle.current) * 0.08
    groupRef.current.rotation.y = currentAngle.current

    // Wheel rotation
    const speed = Math.abs(currentPos.current.x - prevX) + Math.abs(currentPos.current.z - prevZ)
    wheelRot.current += speed * 0.3

    // Hazard light blinking
    const blink = Math.sin(t * 5) > 0 ? 3 : 0
    if (leftEyeRef.current) leftEyeRef.current.material.emissiveIntensity = blink
    if (rightEyeRef.current) rightEyeRef.current.material.emissiveIntensity = blink
  })

  return (
    <group ref={groupRef} position={[x * SCALE, 0, y * SCALE]}>
      {/* ── BODY CHASSIS ── */}
      <mesh position={[0, 2.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[5, 3.5, 4]} />
        <meshStandardMaterial color="#F5A623" roughness={0.4} metalness={0.7} />
      </mesh>

      {/* ── CABIN / SENSOR TOWER ── */}
      <mesh position={[0, 5.5, -0.5]} castShadow>
        <boxGeometry args={[3, 3, 2.5]} />
        <meshStandardMaterial color="#E09010" roughness={0.4} metalness={0.6} />
      </mesh>
      {/* Sensor panel (front of cabin) */}
      <mesh position={[0, 5.5, 0.8]}>
        <boxGeometry args={[2.5, 2.2, 0.1]} />
        <meshStandardMaterial color="#222" roughness={0.3} metalness={0.8} />
      </mesh>
      {/* Robot sensor eyes */}
      <mesh ref={leftEyeRef} position={[-0.6, 5.8, 0.9]}>
        <sphereGeometry args={[0.2, 8, 8]} />
        <meshStandardMaterial color="#00ff00" emissive="#00ff00" emissiveIntensity={3} />
      </mesh>
      <mesh ref={rightEyeRef} position={[0.6, 5.8, 0.9]}>
        <sphereGeometry args={[0.2, 8, 8]} />
        <meshStandardMaterial color="#00ff00" emissive="#00ff00" emissiveIntensity={3} />
      </mesh>

      {/* ── MAST ── */}
      <mesh position={[0, 4.5, 2.8]} castShadow>
        <boxGeometry args={[0.5, 8, 0.5]} />
        <meshStandardMaterial color="#888" roughness={0.5} metalness={0.5} />
      </mesh>

      {/* ── FORK PRONGS ── */}
      <mesh position={[-0.8, 0.5, 4.3]} castShadow>
        <boxGeometry args={[0.6, 0.3, 3]} />
        <meshStandardMaterial color="#777" roughness={0.5} metalness={0.5} />
      </mesh>
      <mesh position={[0.8, 0.5, 4.3]} castShadow>
        <boxGeometry args={[0.6, 0.3, 3]} />
        <meshStandardMaterial color="#777" roughness={0.5} metalness={0.5} />
      </mesh>

      {/* ── WHEELS (4) ── */}
      {[
        [-2.2, 1, -1.5],
        [2.2, 1, -1.5],
        [-2.2, 1, 1.5],
        [2.2, 1, 1.5],
      ].map((pos, i) => (
        <mesh
          key={`wheel-${i}`}
          position={pos}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
        >
          <cylinderGeometry args={[1, 1, 0.6, 12]} />
          <meshStandardMaterial color="#222" roughness={0.8} metalness={0.2} />
        </mesh>
      ))}

      {/* ── HAZARD LIGHTS (top corners) ── */}
      <mesh position={[-1.3, 7.2, -0.5]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color="#FF4400" emissive="#FF4400" emissiveIntensity={0} />
      </mesh>
      <mesh position={[1.3, 7.2, -0.5]}>
        <sphereGeometry args={[0.3, 8, 8]} />
        <meshStandardMaterial color="#FF4400" emissive="#FF4400" emissiveIntensity={0} />
      </mesh>

      {/* ── Headlight glow ── */}
      <pointLight position={[0, 3, 4]} color="#fff5e0" intensity={3} distance={12} />
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   RANDOM_WALK → HUMAN WORKER (safety vest, hard hat)
   ═══════════════════════════════════════════════════════════ */
function HumanWorker({ x, y }) {
  const groupRef = useRef()
  const currentPos = useRef(new THREE.Vector3(x * SCALE, 0, y * SCALE))
  const currentAngle = useRef(0)

  const targetPos = useMemo(
    () => new THREE.Vector3(x * SCALE, 0, y * SCALE),
    [x, y]
  )

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.elapsedTime

    const prevX = currentPos.current.x
    const prevZ = currentPos.current.z
    currentPos.current.lerp(targetPos, 0.18)
    groupRef.current.position.copy(currentPos.current)

    // Face direction of movement
    const moveDx = currentPos.current.x - prevX
    const moveDz = currentPos.current.z - prevZ
    if (Math.abs(moveDx) > 0.001 || Math.abs(moveDz) > 0.001) {
      const ta = Math.atan2(moveDx, moveDz)
      currentAngle.current += (ta - currentAngle.current) * 0.1
    }
    groupRef.current.rotation.y = currentAngle.current
  })

  return (
    <group ref={groupRef} position={[x * SCALE, 0, y * SCALE]}>
      <AnimatedHumanBody />
    </group>
  )
}

function AnimatedHumanBody() {
  const leftArmRef = useRef()
  const rightArmRef = useRef()
  const leftLegRef = useRef()
  const rightLegRef = useRef()
  const headRef = useRef()

  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    const swing = Math.sin(t * 4) * 0.4

    // Arm swing
    if (leftArmRef.current) leftArmRef.current.rotation.x = swing
    if (rightArmRef.current) rightArmRef.current.rotation.x = -swing
    // Leg swing
    if (leftLegRef.current) leftLegRef.current.rotation.x = -swing * 0.6
    if (rightLegRef.current) rightLegRef.current.rotation.x = swing * 0.6
    // Head bob
    if (headRef.current) headRef.current.position.y = 7.5 + Math.sin(t * 1.2) * 0.05
  })

  return (
    <group>
      {/* ── HEAD ── */}
      <group ref={headRef} position={[0, 7.5, 0]}>
        <mesh castShadow>
          <sphereGeometry args={[0.9, 12, 12]} />
          <meshStandardMaterial color="#FDBCB4" roughness={0.8} />
        </mesh>
        {/* Hard hat brim */}
        <mesh position={[0, 0.6, 0]}>
          <cylinderGeometry args={[1.1, 1.1, 0.3, 12]} />
          <meshStandardMaterial color="#FFFF00" roughness={0.5} />
        </mesh>
        {/* Hard hat dome */}
        <mesh position={[0, 0.9, 0]}>
          <cylinderGeometry args={[0.8, 0.9, 0.6, 12]} />
          <meshStandardMaterial color="#FFFF00" roughness={0.5} />
        </mesh>
      </group>

      {/* ── TORSO (orange safety vest) ── */}
      <mesh position={[0, 5.3, 0]} castShadow>
        <boxGeometry args={[2, 3, 1.2]} />
        <meshStandardMaterial color="#FF6B00" roughness={0.7} />
      </mesh>
      {/* Reflective stripes */}
      <mesh position={[0, 5.8, 0.62]}>
        <boxGeometry args={[2.05, 0.2, 0.05]} />
        <meshStandardMaterial
          color="#FFFFFF"
          emissive="#FFFFFF"
          emissiveIntensity={0.3}
        />
      </mesh>
      <mesh position={[0, 4.9, 0.62]}>
        <boxGeometry args={[2.05, 0.2, 0.05]} />
        <meshStandardMaterial
          color="#FFFFFF"
          emissive="#FFFFFF"
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* ── ARMS ── */}
      {/* Left arm */}
      <group ref={leftArmRef} position={[-1.35, 6.2, 0]}>
        <mesh position={[0, -1.25, 0]} castShadow>
          <boxGeometry args={[0.7, 2.5, 0.7]} />
          <meshStandardMaterial color="#FF6B00" roughness={0.7} />
        </mesh>
      </group>
      {/* Right arm */}
      <group ref={rightArmRef} position={[1.35, 6.2, 0]}>
        <mesh position={[0, -1.25, 0]} castShadow>
          <boxGeometry args={[0.7, 2.5, 0.7]} />
          <meshStandardMaterial color="#FF6B00" roughness={0.7} />
        </mesh>
      </group>

      {/* ── LEGS ── */}
      {/* Left leg */}
      <group ref={leftLegRef} position={[-0.55, 3.5, 0]}>
        <mesh position={[0, -1.5, 0]} castShadow>
          <boxGeometry args={[0.9, 3, 0.9]} />
          <meshStandardMaterial color="#1a1a5c" roughness={0.8} />
        </mesh>
        {/* Boot */}
        <mesh position={[0, -3.2, 0.25]} castShadow>
          <boxGeometry args={[1, 0.8, 1.5]} />
          <meshStandardMaterial color="#3d2b1f" roughness={0.9} />
        </mesh>
      </group>
      {/* Right leg */}
      <group ref={rightLegRef} position={[0.55, 3.5, 0]}>
        <mesh position={[0, -1.5, 0]} castShadow>
          <boxGeometry args={[0.9, 3, 0.9]} />
          <meshStandardMaterial color="#1a1a5c" roughness={0.8} />
        </mesh>
        {/* Boot */}
        <mesh position={[0, -3.2, 0.25]} castShadow>
          <boxGeometry args={[1, 0.8, 1.5]} />
          <meshStandardMaterial color="#3d2b1f" roughness={0.9} />
        </mesh>
      </group>
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   CONTAINER — routes to sub-components by type
   ═══════════════════════════════════════════════════════════ */

export default function Obstacles({ obstacles }) {
  if (!obstacles || obstacles.length === 0) return null

  return (
    <group>
      {obstacles.map((obs) => {
        switch (obs.type) {
          case 'static':
            return <ShelfUnit key={obs.id} x={obs.x} y={obs.y} />
          case 'patrol':
            return (
              <ForkLift
                key={obs.id}
                x={obs.x}
                y={obs.y}
                dx={obs.dx}
                dy={obs.dy}
              />
            )
          case 'random_walk':
            return <HumanWorker key={obs.id} x={obs.x} y={obs.y} />
          default:
            return null
        }
      })}
    </group>
  )
}
