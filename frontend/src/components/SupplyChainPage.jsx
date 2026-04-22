import React, { useState, useEffect } from 'react';
import { ArrowLeft, Truck } from 'lucide-react';
import { subscribeToWarehouseQueues } from '../lib/firebase';
import OrderForm from './supply/OrderForm';
import OrderConfirmationCard from './supply/OrderConfirmationCard';
import WarehouseQueuePanel from './supply/WarehouseQueuePanel';
import WarehouseIntelligenceCard from './supply/WarehouseIntelligenceCard';
import SystemHealthCard from './supply/SystemHealthCard';

export default function SupplyChainPage({ onBack, onContinue }) {
  const [warehouses, setWarehouses] = useState(null);
  const [orderResult, setOrderResult] = useState(null);
  const [highlightWh, setHighlightWh] = useState(null);

  // Firebase real-time listener
  useEffect(() => {
    const unsub = subscribeToWarehouseQueues((data) => {
      setWarehouses(data);
    });
    return () => {
      if (typeof unsub === 'function') unsub();
    };
  }, []);

  const handleOrderPlaced = (result) => {
    setOrderResult(result);
    setHighlightWh(result.warehouse);
    setTimeout(() => setHighlightWh(null), 1200);
  };

  return (
    <div className="w-screen min-h-screen bg-[#050505] text-gray-300 overflow-y-auto overflow-x-hidden font-sans selection:bg-blue-900 selection:text-blue-100">

      {/* Background ambient gradients */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-300/[0.06] blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-300/[0.06] blur-[120px]" />
      </div>

      {/* Top Nav */}
      <nav className="w-full max-w-[100rem] mx-auto px-8 md:px-12 py-6 flex items-center justify-between z-10 relative">
        <div className="flex items-center gap-2 font-black text-2xl tracking-tighter cursor-default select-none text-white">
          <div className="w-3.5 h-3.5 bg-gradient-to-tr from-blue-300 to-purple-300 rounded-full shadow-[0_0_8px_rgba(147,197,253,0.5)]" />
          WAREFLOW
        </div>

        <div className="hidden md:flex gap-10 font-bold text-sm tracking-wide text-gray-400">
          <button onClick={onBack} className="hover:text-blue-300 transition-colors">STORE</button>
          <button className="text-blue-300 border-b-2 border-blue-300/50 pb-0.5">SUPPLY CHAIN</button>
          <button onClick={onContinue} className="hover:text-blue-300 transition-colors">WAREHOUSE</button>
        </div>
      </nav>

      {/* Page Header */}
      <div className="max-w-[100rem] mx-auto px-8 md:px-12 relative z-10">
        <header className="mb-10 flex flex-col items-center border-b border-gray-800/50 pb-6">
          <div className="h-[1px] w-48 bg-gradient-to-r from-transparent via-blue-300 to-transparent mb-5 opacity-30" />
          <h1 className="text-3xl font-light tracking-[0.15em] text-gray-300 mb-2 uppercase">
            SUPPLY <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300">CHAIN</span>
          </h1>
          <p className="text-[#646464] uppercase tracking-[0.3em] text-[0.65rem] font-mono">
            ML-Powered Warehouse Intelligence
          </p>
          <div className="h-[1px] w-48 bg-gradient-to-r from-transparent via-purple-300 to-transparent mt-5 opacity-30" />
        </header>

        {/* Split Layout */}
        <div className="flex flex-col lg:flex-row gap-6 pb-16">

          {/* Left Column — 45% */}
          <div className="w-full lg:w-[45%] space-y-6">
            <OrderForm onOrderPlaced={handleOrderPlaced} />
            <OrderConfirmationCard orderResult={orderResult} />
            <WarehouseQueuePanel warehouses={warehouses} highlightWh={highlightWh} />
          </div>

          {/* Right Column — 55% */}
          <div className="w-full lg:w-[55%] space-y-6">
            <WarehouseIntelligenceCard />
            <SystemHealthCard />

            {/* Navigation CTA */}
            <div className="flex gap-3">
              <button
                onClick={onBack}
                className="flex-1 flex items-center justify-center gap-2 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.06] text-gray-300 font-bold text-sm tracking-wider uppercase py-3.5 px-6 rounded-full transition-all"
                aria-label="Back to Store"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Store
              </button>
              <button
                onClick={onContinue}
                className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300 hover:opacity-90 text-indigo-950 font-extrabold text-sm tracking-wider uppercase py-3.5 px-6 rounded-full transition-all transform hover:-translate-y-0.5"
                aria-label="Go to Warehouse View"
              >
                <Truck className="w-4 h-4" />
                Warehouse View
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
