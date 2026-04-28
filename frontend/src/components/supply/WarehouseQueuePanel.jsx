import React, { useState, useEffect, useRef } from 'react';
import { MapPin } from 'lucide-react';

export default function WarehouseQueuePanel({ warehouses, highlightWh }) {
  const [lastSynced, setLastSynced] = useState(Date.now());
  const [timeAgo, setTimeAgo] = useState('just now');
  const prevQueues = useRef({});
  const [flashWh, setFlashWh] = useState(null);

  // Update "time ago" every second
  useEffect(() => {
    const interval = setInterval(() => {
      const seconds = Math.round((Date.now() - lastSynced) / 1000);
      setTimeAgo(seconds < 2 ? 'just now' : `${seconds}s ago`);
    }, 1000);
    return () => clearInterval(interval);
  }, [lastSynced]);

  // Detect queue changes and flash
  useEffect(() => {
    if (!warehouses) return;
    setLastSynced(Date.now());

    Object.entries(warehouses).forEach(([whId, data]) => {
      const prev = prevQueues.current[whId];
      if (prev !== undefined && prev !== data.pending) {
        setFlashWh(whId);
        setTimeout(() => setFlashWh(null), 800);
      }
    });

    prevQueues.current = Object.fromEntries(
      Object.entries(warehouses).map(([id, d]) => [id, d.pending])
    );
  }, [warehouses]);

  // Also flash when highlightWh changes (order just placed)
  useEffect(() => {
    if (highlightWh) {
      setFlashWh(highlightWh);
      setTimeout(() => setFlashWh(null), 800);
    }
  }, [highlightWh]);

  const getBarColor = (pending) => {
    if (pending <= 3) return 'bg-emerald-500';
    if (pending <= 6) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const VALID_WAREHOUSES = ['delhi', 'mumbai', 'bangalore', 'hyderabad', 'chennai', 'kolkata', 'lucknow', 'jaipur', 'ahmedabad', 'pune'];

  const warehouseEntries = warehouses 
    ? Object.entries(warehouses).filter(([id]) => VALID_WAREHOUSES.includes(id.toLowerCase()))
    : [];

  // Loading skeleton
  if (!warehouses) {
    return (
      <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6">
        <div className="h-5 w-48 bg-white/[0.06] rounded animate-pulse mb-2" />
        <div className="h-3 w-64 bg-white/[0.04] rounded animate-pulse mb-6" />
        <div className="space-y-4">
          <div className="h-10 bg-white/[0.04] rounded-lg animate-pulse" />
          <div className="h-10 bg-white/[0.04] rounded-lg animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6 transition-all duration-300">
      {/* Title */}
      <div className="flex items-center gap-3 mb-1">
        <MapPin className="w-5 h-5 text-purple-300" />
        <h2 className="text-lg font-bold text-white tracking-tight">Live Warehouse Queues</h2>
      </div>
      <p className="text-[#646464] text-xs font-mono tracking-wide mb-5 ml-8">
        Updates in real time via Firebase
      </p>

      {/* Queue bars */}
      <div className="space-y-4">
        {warehouseEntries.map(([whId, data]) => {
          const pending = data.pending || 0;
          const name = whId.charAt(0).toUpperCase() + whId.slice(1);
          const barWidth = Math.min((pending / 10) * 100, 100);
          const isFlashing = flashWh === whId;

          return (
            <div
              key={whId}
              className={`flex items-center gap-4 p-3 rounded-xl transition-all duration-300 ${
                isFlashing
                  ? 'bg-blue-300/10 border border-blue-300/30 shadow-[0_0_15px_rgba(147,197,253,0.2)]'
                  : 'bg-white/[0.02] border border-transparent'
              }`}
            >
              {/* Name */}
              <div className="flex items-center gap-2 min-w-[100px]">
                <MapPin className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-sm text-gray-300 font-semibold">{name}</span>
              </div>

              {/* Bar */}
              <div className="flex-1 h-3 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-[600ms] ease-in-out ${getBarColor(pending)}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              {/* Count */}
              <span className="text-xs font-mono text-gray-400 min-w-[80px] text-right">
                <span className="text-white font-bold">{pending}</span> pending
              </span>
            </div>
          );
        })}
      </div>

      {/* Last synced */}
      <p className="text-[0.6rem] text-gray-600 font-mono mt-4 text-center">
        Last synced: {timeAgo}
      </p>
    </div>
  );
}
