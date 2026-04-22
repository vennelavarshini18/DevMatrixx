import React, { useState, useEffect } from 'react';
import { CheckCircle, Clock, Package, Cpu, Warehouse } from 'lucide-react';

export default function OrderConfirmationCard({ orderResult }) {
  const [isFaded, setIsFaded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (orderResult) {
      setIsFaded(false);
      // Trigger mount animation
      requestAnimationFrame(() => setIsVisible(true));

      // Auto-fade after 30s
      const timer = setTimeout(() => setIsFaded(true), 30000);
      return () => clearTimeout(timer);
    }
  }, [orderResult]);

  if (!orderResult) return null;

  const { warehouse, eta, queue_position, elapsed_ms } = orderResult;
  const whName = warehouse.charAt(0).toUpperCase() + warehouse.slice(1);

  return (
    <div
      className={`bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6 transition-all duration-500 ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
        ${isFaded ? 'opacity-40' : ''}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle className="w-5 h-5 text-emerald-400" />
        <h3 className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-purple-300 font-bold text-lg">
          Order Assigned
        </h3>
      </div>

      {/* Warehouse Badge */}
      <div className="flex items-center gap-3 mb-5 p-3 bg-white/[0.04] rounded-xl border border-blue-300/20">
        <Warehouse className="w-6 h-6 text-blue-300" />
        <span
          className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-purple-300 tracking-tight"
          style={{ textShadow: '0 0 20px rgba(147,197,253,0.3)' }}
        >
          {whName}
        </span>
        <span className="text-[0.6rem] text-gray-500 font-mono uppercase ml-auto">Warehouse</span>
      </div>

      {/* Metric Chips */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-white/[0.04] border border-white/[0.06] rounded-xl p-3 text-center">
          <Clock className="w-4 h-4 text-blue-300 mx-auto mb-1" />
          <p className="text-[0.6rem] text-gray-500 font-mono uppercase">ETA</p>
          <p className="text-white font-bold text-sm font-mono">{eta}</p>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.06] rounded-xl p-3 text-center">
          <Package className="w-4 h-4 text-purple-300 mx-auto mb-1" />
          <p className="text-[0.6rem] text-gray-500 font-mono uppercase">Queue Pos</p>
          <p className="text-white font-bold text-sm font-mono">#{queue_position}</p>
        </div>
        <div className="bg-white/[0.04] border border-white/[0.06] rounded-xl p-3 text-center">
          <Cpu className="w-4 h-4 text-indigo-300 mx-auto mb-1" />
          <p className="text-[0.6rem] text-gray-500 font-mono uppercase">Model</p>
          <p className="text-white font-bold text-sm font-mono">XGBoost</p>
        </div>
      </div>

      {/* Footer */}
      <p className="text-[0.6rem] text-gray-600 font-mono text-center">
        Assigned in {elapsed_ms}ms &bull; Powered by XGBoost + Google Maps
      </p>
    </div>
  );
}
