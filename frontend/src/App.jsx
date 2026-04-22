import { useState, useEffect, useRef } from 'react'
import LandingPage from './components/LandingPage'
import WarehouseScene from './components/WarehouseScene'
import HUD from './components/HUD'
import CustomerForm from './components/CustomerForm'
import SupplyChainPage from './components/SupplyChainPage'
import SupplyChainDashboard from './components/supply/SupplyChainDashboard'
import useWarehouseSocket from './hooks/useWarehouseSocket'

export default function App() {
  const [currentView, setCurrentView] = useState('landing')
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

  if (currentView === 'landing') {
    return <LandingPage onGetStarted={() => setCurrentView('store')} onSupplyChain={() => setCurrentView('supplyDashboard')} />
  }

  if (currentView === 'store') {
    return <CustomerForm onOrderPlaced={() => setCurrentView('supply')} />
  }

  // Person 4's Supply Chain Order Page (order flow → warehouse)
  if (currentView === 'supply') {
    return (
      <SupplyChainPage
        onBack={() => setCurrentView('store')}
        onContinue={() => setCurrentView('warehouse')}
      />
    )
  }

  // Person 3's Route Optimizer Dashboard (map, simulation, storm demo)
  if (currentView === 'supplyDashboard') {
    return <SupplyChainDashboard onBack={() => setCurrentView('landing')} />
  }

  return (
    <div className="w-screen h-screen bg-black relative overflow-hidden">
      <WarehouseScene frameData={frameData} connectionStatus={connectionStatus} />
      <HUD
        frameData={frameData}
        speedMultiplier={speedMultiplier}
        onSpeedChange={setSpeedMultiplier}
        onBack={() => setCurrentView('supply')}
        onSupplyChain={() => setCurrentView('supplyDashboard')}
      />

      {/* Flash Overlay */}
      <div
        className={`pointer-events-none absolute inset-0 transition-opacity duration-[600ms] ease-out z-[100] ${flashColor ? 'opacity-40 ' + flashColor : 'opacity-0 bg-transparent'}`}
      />
    </div>
  )
}
