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

const TEST_OBSTACLES = []

export default function WarehouseScene({ frameData, connectionStatus }) {
  const [activePreset, setActivePreset] = useState(null)

  const agentData = frameData?.agent || { x: 7, y: 9, status: 'moving' }
  const goalData = frameData?.goal || { x: 14, y: 14 }
  const obstaclesData = frameData?.obstacles || TEST_OBSTACLES
  
  const targetCategory = frameData?.target_category || ''
  const routeStage = frameData?.route_stage || 'to_shelf'
  const deliveryPos = frameData?.delivery_pos || { x: 14, y: 14 }

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
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 bg-gray-900/80 p-2 border border-white/10 rounded-md backdrop-blur-sm whitespace-nowrap shadow-lg">
              <div className={`w-3 h-3 rounded-full ${statusColor} ${connectionStatus === 'connecting' ? 'animate-pulse' : ''}`} />
              <span className="text-sm font-semibold text-white">{statusText}</span>
            </div>
            
            {targetCategory && (
              <div className="bg-[#1a1c23]/90 p-3 border-l-4 border-emerald-500 rounded-r-md backdrop-blur-md shadow-[0_4px_15px_rgba(0,0,0,0.5)] min-w-[200px]">
                <div className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider mb-1">
                  Active Mission
                </div>
                <div className="text-sm font-semibold text-white">
                  {routeStage === 'to_shelf' 
                    ? `Pick up: ${targetCategory}` 
                    : `Deliver: ${targetCategory} to Exit`}
                </div>
              </div>
            )}
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

        {/* Delivery Zone (Static Drop-off marker) */}
        <group position={[deliveryPos.x * SCALE, 0.1, deliveryPos.y * SCALE]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[SCALE * 0.9, SCALE * 0.9]} />
            <meshBasicMaterial color="#ffaa00" transparent opacity={0.3} />
          </mesh>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
            <ringGeometry args={[SCALE * 0.35, SCALE * 0.45, 32]} />
            <meshBasicMaterial color="#ffaa00" />
          </mesh>
          <Html position={[0, 4, 0]} center style={{ pointerEvents: 'none' }}>
            <div className="text-[#ffaa00] font-bold text-[10px] uppercase tracking-widest text-shadow-sm whitespace-nowrap">
              Delivery Zone
            </div>
          </Html>
        </group>

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