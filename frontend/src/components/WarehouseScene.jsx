import { useState, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import WarehouseEnvironment from './WarehouseEnvironment'
import Floor from './Floor'
import { CameraControls, CameraPresetButtons } from './CameraRig'
import Agent from './Agent'
import GoalTile from './GoalTile'
import Obstacles from './Obstacles'

const SCALE = 100 / 15

const TEST_OBSTACLES = [
  { id: 's_0', x: 3,  y: 4,  type: 'static' },
  { id: 's_1', x: 6,  y: 9,  type: 'static' },
  { id: 'p_0', x: 8,  y: 2,  type: 'patrol', dx: 1, dy: 0 },
  { id: 'p_1', x: 1,  y: 12, type: 'patrol', dx: 0, dy: -1 },
  { id: 'r_0', x: 11, y: 6,  type: 'random_walk' },
  { id: 'r_1', x: 4,  y: 10, type: 'random_walk' },
]

export default function WarehouseScene({ frameData, connectionStatus }) {
  const [activePreset, setActivePreset] = useState(null)

  const agentData = frameData?.agent || { x: 7, y: 9, status: 'moving' }
  const goalData = frameData?.goal || { x: 14, y: 14 }
  const obstaclesData = frameData?.obstacles || TEST_OBSTACLES

  const trailRef = useRef([])
  const lastPos = trailRef.current[trailRef.current.length - 1]
  if (frameData?.agent && (!lastPos || lastPos.x !== agentData.x || lastPos.y !== agentData.y)) {
    trailRef.current.push({ x: agentData.x, y: agentData.y })
    if (trailRef.current.length > 20) {
      trailRef.current.shift()
    }
  }

  let statusColor = 'bg-yellow-500'
  let statusText = 'Connecting...'
  if (connectionStatus === 'connected') {
    statusColor = 'bg-green-500'
    statusText = 'Live'
  } else if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
    statusColor = 'bg-red-500'
    statusText = 'Disconnected'
  }

  return (
    <div className="relative w-full h-full">
      <Canvas
        shadows
        camera={{ position: [60, 80, 60], fov: 50, near: 0.1, far: 1000 }}
        style={{ background: '#000' }}
      >
        <Html position={[0, 0, 0]} center style={{ pointerEvents: 'none', top: '-45vh', left: '-45vw' }}>
          <div className="flex items-center gap-2 bg-gray-900/80 p-2 border border-white/10 rounded-md backdrop-blur-sm whitespace-nowrap">
            <div className={`w-3 h-3 rounded-full ${statusColor} ${connectionStatus === 'connecting' ? 'animate-pulse' : ''}`} />
            <span className="text-sm font-semibold text-white">{statusText}</span>
          </div>
        </Html>

        {/* Environment — floor, walls, ceiling, lights, atmosphere */}
        <WarehouseEnvironment />

        {/* Trail Renderer */}
        {trailRef.current.map((pos, index) => (
          <mesh key={`trail-${index}`} position={[pos.x * SCALE, 0.2, pos.y * SCALE]}>
            <cylinderGeometry args={[1, 1, 0.2, 8]} />
            <meshStandardMaterial color="#00d4ff" opacity={(index + 1) / 20} transparent />
          </mesh>
        ))}

        {/* Scene objects (render order: back → front) */}
        <GoalTile x={goalData.x} y={goalData.y} />
        <Obstacles obstacles={obstaclesData} />
        <Agent x={agentData.x} y={agentData.y} status={agentData.status} />

        {/* Camera controls */}
        <CameraControls preset={activePreset} />
      </Canvas>

      {/* HTML overlay — camera preset buttons */}
      <CameraPresetButtons onPreset={setActivePreset} />
    </div>
  )
}
