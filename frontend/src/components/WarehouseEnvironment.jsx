import { useMemo } from 'react'

/**
 * WarehouseEnvironment — floor, walls, ceiling, columns, lights, atmosphere.
 * Renders everything that is NOT an agent or obstacle.
 */
export default function WarehouseEnvironment() {
  return (
    <group>
      {/* ── Global atmosphere ── */}
      <ambientLight intensity={0.4} />
      <fog attach="fog" args={['#0d0d0d', 80, 250]} />

      <ConcreteFloor />
      <AisleMarkings />
      <PerimeterMarkings />
      <SupportColumns />
      <Ceiling />
      <HangingLights />
      <Walls />
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   CONCRETE FLOOR
   ═══════════════════════════════════════════════════════════ */
function ConcreteFloor() {
  return (
    <group>
      {/* Base concrete slab */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[50, -0.05, 50]}
        receiveShadow
      >
        <planeGeometry args={[100, 100]} />
        <meshStandardMaterial color="#2a2a2a" roughness={0.9} metalness={0.05} />
      </mesh>

      {/* Very subtle grid overlay for cell reference */}
      <gridHelper args={[100, 15, '#3a3a3a', '#2d2d2d']} position={[50, 0.01, 50]} />
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   YELLOW FORKLIFT AISLE MARKINGS
   ═══════════════════════════════════════════════════════════ */
function AisleMarkings() {
  const lines = useMemo(() => {
    const result = []
    // Yellow lines running along Z every ~20 units on X
    for (let xPos = 20; xPos <= 80; xPos += 20) {
      result.push({ x: xPos, z: 50 })
    }
    return result
  }, [])

  return (
    <group>
      {lines.map((line, i) => (
        <mesh
          key={`aisle-${i}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[line.x, 0.02, line.z]}
        >
          <planeGeometry args={[0.4, 100]} />
          <meshStandardMaterial
            color="#c8a820"
            transparent
            opacity={0.5}
            roughness={0.7}
          />
        </mesh>
      ))}
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   WHITE DASHED PERIMETER MARKINGS
   ═══════════════════════════════════════════════════════════ */
function PerimeterMarkings() {
  const dashes = useMemo(() => {
    const result = []
    const dashLen = 3
    const gapLen = 2
    const total = dashLen + gapLen

    // Top edge (Z=0) and bottom edge (Z=100)
    for (let x = 1; x < 100; x += total) {
      result.push({ px: x + dashLen / 2, pz: 0.5, rx: dashLen, rz: 0.35 })
      result.push({ px: x + dashLen / 2, pz: 99.5, rx: dashLen, rz: 0.35 })
    }
    // Left edge (X=0) and right edge (X=100)
    for (let z = 1; z < 100; z += total) {
      result.push({ px: 0.5, pz: z + dashLen / 2, rx: 0.35, rz: dashLen })
      result.push({ px: 99.5, pz: z + dashLen / 2, rx: 0.35, rz: dashLen })
    }
    return result
  }, [])

  return (
    <group>
      {dashes.map((d, i) => (
        <mesh
          key={`perim-${i}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[d.px, 0.025, d.pz]}
        >
          <planeGeometry args={[d.rx, d.rz]} />
          <meshStandardMaterial color="#ffffff" transparent opacity={0.25} />
        </mesh>
      ))}
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   SUPPORT COLUMNS + CROSS BEAMS
   ═══════════════════════════════════════════════════════════ */
function SupportColumns() {
  const columns = [
    [10, 10],
    [10, 90],
    [90, 10],
    [90, 90],
  ]

  return (
    <group>
      {/* Vertical columns */}
      {columns.map(([cx, cz], i) => (
        <mesh key={`col-${i}`} position={[cx, 15, cz]} castShadow>
          <boxGeometry args={[1.5, 30, 1.5]} />
          <meshStandardMaterial 
            color="#ffaa00" 
            roughness={0.6} 
            metalness={0.4} 
            emissive="#ffaa00" 
            emissiveIntensity={0.2} 
          />
        </mesh>
      ))}

      {/* Cross beams along X at Z=10 and Z=90 */}
      {[10, 90].map((z) => (
        <mesh key={`beam-x-${z}`} position={[50, 29, z]}>
          <boxGeometry args={[80, 0.8, 0.8]} />
          <meshStandardMaterial 
            color="#dd8800" 
            roughness={0.6} 
            metalness={0.4} 
            emissive="#dd8800" 
            emissiveIntensity={0.2} 
          />
        </mesh>
      ))}
      {/* Cross beams along Z at X=10 and X=90 */}
      {[10, 90].map((x) => (
        <mesh key={`beam-z-${x}`} position={[x, 29, 50]}>
          <boxGeometry args={[0.8, 0.8, 80]} />
          <meshStandardMaterial 
            color="#dd8800" 
            roughness={0.6} 
            metalness={0.4} 
            emissive="#dd8800" 
            emissiveIntensity={0.2} 
          />
        </mesh>
      ))}
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   CEILING
   ═══════════════════════════════════════════════════════════ */
function Ceiling() {
  return (
    <mesh rotation={[Math.PI / 2, 0, 0]} position={[50, 30, 50]}>
      <planeGeometry args={[100, 100]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.9} />
    </mesh>
  )
}

/* ═══════════════════════════════════════════════════════════
   HANGING INDUSTRIAL LIGHTS (2×3 grid)
   ═══════════════════════════════════════════════════════════ */
function HangingLights() {
  const positions = useMemo(() => {
    const lights = []
    for (let ix = 0; ix < 2; ix++) {
      for (let iz = 0; iz < 3; iz++) {
        lights.push([20 + ix * 60, 28, 18 + iz * 32])
      }
    }
    return lights
  }, [])

  return (
    <group>
      {positions.map(([lx, ly, lz], i) => (
        <group key={`light-${i}`}>
          {/* Fixture body (grey housing) */}
          <mesh position={[lx, ly + 1, lz]}>
            <boxGeometry args={[2, 0.5, 2]} />
            <meshStandardMaterial color="#666" roughness={0.5} metalness={0.4} />
          </mesh>
          {/* Cable to ceiling */}
          <mesh position={[lx, ly + 1.75, lz]}>
            <cylinderGeometry args={[0.08, 0.08, 1, 6]} />
            <meshStandardMaterial color="#444" />
          </mesh>
          {/* Spotlight with cone */}
          <spotLight
            position={[lx, ly, lz]}
            angle={0.5}
            penumbra={0.4}
            intensity={40}
            distance={45}
            color="#fff5e0"
            castShadow
            shadow-mapSize-width={512}
            shadow-mapSize-height={512}
          />
          {/* Glow bulb indicator */}
          <mesh position={[lx, ly, lz]}>
            <sphereGeometry args={[0.3, 8, 8]} />
            <meshStandardMaterial
              color="#fff5e0"
              emissive="#fff5e0"
              emissiveIntensity={3}
            />
          </mesh>
        </group>
      ))}
    </group>
  )
}

/* ═══════════════════════════════════════════════════════════
   CORRUGATED METAL WALLS + HIGH WINDOWS
   ═══════════════════════════════════════════════════════════ */
function Walls() {
  const panelColors = ['#363636', '#3d3d3d']

  // Generate corrugated wall panels for one wall
  const renderWall = (wallKey, position, rotation, length) => {
    const panelWidth = length / 8
    const panels = []
    for (let i = 0; i < 8; i++) {
      const offset = -length / 2 + panelWidth / 2 + i * panelWidth
      panels.push({
        offset,
        color: panelColors[i % 2],
      })
    }

    // High windows (3 per wall, near top)
    const windows = [-30, 0, 30].map((wo) => wo)

    return (
      <group key={wallKey} position={position} rotation={rotation}>
        {/* Corrugated panels */}
        {panels.map((p, i) => (
          <mesh key={`panel-${i}`} position={[p.offset, 15, 0]}>
            <planeGeometry args={[panelWidth - 0.1, 30]} />
            <meshStandardMaterial color={p.color} roughness={0.7} metalness={0.3} />
          </mesh>
        ))}

        {/* High windows — small emissive patches */}
        {windows.map((wo, wi) => (
          <mesh key={`win-${wi}`} position={[wo, 25, 0.05]}>
            <planeGeometry args={[4, 2]} />
            <meshStandardMaterial
              color="#aabbcc"
              emissive="#c8d8e8"
              emissiveIntensity={0.4}
              transparent
              opacity={0.5}
            />
          </mesh>
        ))}
      </group>
    )
  }

  return (
    <group>
      {/* North wall (Z=0) */}
      {renderWall('north', [50, 0, 0], [0, 0, 0], 100)}
      {/* South wall (Z=100) */}
      {renderWall('south', [50, 0, 100], [0, Math.PI, 0], 100)}
      {/* West wall (X=0) */}
      {renderWall('west', [0, 0, 50], [0, Math.PI / 2, 0], 100)}
      {/* East wall (X=100) */}
      {renderWall('east', [100, 0, 50], [0, -Math.PI / 2, 0], 100)}
    </group>
  )
}
