import { useState, useEffect, useRef } from 'react'
import WarehouseScene from './components/WarehouseScene'
import HUD from './components/HUD'
import useWarehouseSocket from './hooks/useWarehouseSocket'

export default function App() {
  const [speedMultiplier, setSpeedMultiplier] = useState(1)
  const { frameData, connectionStatus } = useWarehouseSocket('ws://localhost:8000/ws', speedMultiplier)

  const [flashColor, setFlashColor] = useState(null)
  const flashTimeout = useRef(null)

  useEffect(() => {
    if (frameData?.agent?.status === 'collided') {
      setFlashColor('bg-red-500')
      clearTimeout(flashTimeout.current)
      flashTimeout.current = setTimeout(() => setFlashColor(null), 600)
    } else if (frameData?.agent?.status === 'reached_goal') {
      setFlashColor('bg-green-500')
      clearTimeout(flashTimeout.current)
      flashTimeout.current = setTimeout(() => setFlashColor(null), 600)
    }
  }, [frameData?.agent?.status])

  return (
    <div className="w-screen h-screen bg-black relative overflow-hidden">
      <WarehouseScene frameData={frameData} connectionStatus={connectionStatus} />
      <HUD frameData={frameData} speedMultiplier={speedMultiplier} onSpeedChange={setSpeedMultiplier} />
      
      {/* Flash Overlay */}
      <div 
        className={`pointer-events-none absolute inset-0 transition-opacity duration-[600ms] ease-out z-[100] ${flashColor ? 'opacity-40 ' + flashColor : 'opacity-0 bg-transparent'}`} 
      />
    </div>
  )
}
