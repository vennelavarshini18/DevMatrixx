import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Server } from 'lucide-react';

export default function SystemHealthCard() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const pollHealth = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8002/health');
      if (!res.ok) throw new Error('unhealthy');
      const data = await res.json();
      setHealth(data);
      setError(false);
    } catch (e) {
      setError(true);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    pollHealth();
    const interval = setInterval(pollHealth, 30000);
    return () => clearInterval(interval);
  }, [pollHealth]);

  const StatusPill = ({ label, isHealthy, healthyText, unhealthyText }) => (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]' : 'bg-red-400 shadow-[0_0_6px_rgba(248,113,113,0.5)]'}`} />
        <span className="text-sm text-gray-300">{label}</span>
      </div>
      <span className={`text-[0.65rem] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ${
        isHealthy
          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
          : 'bg-red-500/10 text-red-400 border border-red-500/20'
      }`}>
        {isHealthy ? healthyText : unhealthyText}
      </span>
    </div>
  );

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6">
        <div className="h-5 w-32 bg-white/[0.06] rounded animate-pulse mb-4" />
        <div className="space-y-3">
          <div className="h-8 bg-white/[0.04] rounded animate-pulse" />
          <div className="h-8 bg-white/[0.04] rounded animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6 transition-all duration-300">
      {/* Title */}
      <div className="flex items-center gap-3 mb-4">
        <Activity className="w-5 h-5 text-blue-300" />
        <h2 className="text-lg font-bold text-white tracking-tight">System Status</h2>
      </div>

      {/* Statuses */}
      <div className="space-y-1">
        <StatusPill
          label="Firebase"
          isHealthy={!error && health?.firebase_connected}
          healthyText="Connected"
          unhealthyText="Offline"
        />
        <StatusPill
          label="ML Model"
          isHealthy={!error && health?.model_loaded}
          healthyText="Loaded"
          unhealthyText="Not Loaded"
        />
      </div>

      {/* Error message */}
      {error && (
        <p className="text-[0.65rem] text-red-400 font-mono mt-3 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          Backend offline — retrying in 30s
        </p>
      )}

      {/* API Endpoint */}
      <div className="mt-4 pt-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Server className="w-3 h-3 text-gray-600" />
          <span className="text-[0.6rem] text-gray-600 font-mono">
            API: http://localhost:8002
          </span>
        </div>
      </div>
    </div>
  );
}
