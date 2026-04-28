import React, { useEffect, useState, useRef } from 'react';

/**
 * DisruptionCard — Person 2's Disruption Intelligence Widget
 *
 * Polls the main backend (port 8000) endpoint /api/supply/trigger-weather-event
 * to fetch live risk data and display it in the HUD overlay.
 *
 * Also subscribes to Firebase /active_shipment for real-time risk_score + gemini_alert
 * written by Person 2's backend pipeline.
 */

const BACKEND_URL = 'http://localhost:8000';

// Demo scenarios for quick triggering
const SCENARIOS = [
  { id: 'lucknow',  label: 'Lucknow',  lat: 26.8467, lng: 80.9462, city: 'Lucknow' },
  { id: 'agra',     label: 'Agra',     lat: 27.1767, lng: 78.0081, city: 'Agra' },
  { id: 'delhi',    label: 'Delhi',    lat: 28.6139, lng: 77.2090, city: 'Delhi' },
];

export default function DisruptionCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const pulseRef = useRef(null);

  // Fetch disruption data for a given city
  const fetchDisruption = async (scenario) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/supply/trigger-weather-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: scenario.lat,
          lng: scenario.lng,
          city: scenario.city,
          base_travel_time: 4.0,
          source: 'Lucknow',
          destination: 'Delhi',
        }),
      });
      const result = await res.json();
      setData(result);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('[P2 DisruptionCard] Fetch failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // Auto-scan Lucknow on mount
  useEffect(() => {
    fetchDisruption(SCENARIOS[0]);
  }, []);

  // Risk UI helpers
  const riskScore = data?.risk_score ?? null;
  const getRiskConfig = (score) => {
    if (score === null) return {
      label: 'SCANNING',
      color: 'text-gray-400',
      bg: 'bg-gray-800/40',
      border: 'border-gray-700/50',
      glow: '',
      dot: 'bg-gray-500',
    };
    if (score > 0.8) return {
      label: 'CRITICAL',
      color: 'text-red-400',
      bg: 'bg-red-950/50',
      border: 'border-red-500/40',
      glow: 'shadow-[0_0_25px_rgba(239,68,68,0.3)]',
      dot: 'bg-red-400 animate-pulse',
    };
    if (score > 0.7) return {
      label: 'HIGH',
      color: 'text-red-400',
      bg: 'bg-red-950/30',
      border: 'border-red-500/30',
      glow: 'shadow-[0_0_15px_rgba(239,68,68,0.2)]',
      dot: 'bg-red-400',
    };
    if (score > 0.4) return {
      label: 'MODERATE',
      color: 'text-amber-400',
      bg: 'bg-amber-950/30',
      border: 'border-amber-500/30',
      glow: '',
      dot: 'bg-amber-400',
    };
    return {
      label: 'LOW',
      color: 'text-emerald-400',
      bg: 'bg-emerald-950/30',
      border: 'border-emerald-500/30',
      glow: '',
      dot: 'bg-emerald-400',
    };
  };

  const risk = getRiskConfig(riskScore);

  return (
    <div className="w-full pointer-events-auto transition-all duration-300">
      <div className={`bg-[#0a0b14]/95 backdrop-blur-xl rounded-xl border border-white/[0.08] overflow-hidden ${risk.glow} transition-shadow duration-500`}>

        {/* ── Header ─────────────────────────────────────────────────── */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className={`w-2 h-2 rounded-full ${risk.dot}`} />
              {riskScore !== null && riskScore > 0.7 && (
                <div className="absolute inset-0 w-2 h-2 rounded-full bg-red-400 animate-ping opacity-50" />
              )}
            </div>
            <span className="text-[0.6rem] font-bold tracking-[0.2em] uppercase text-gray-400">
              Disruption Intel
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[0.6rem] font-mono font-bold tracking-wider px-2 py-0.5 rounded-full border ${risk.bg} ${risk.border} ${risk.color}`}>
              {risk.label}
            </span>
            <svg
              className={`w-3.5 h-3.5 text-gray-600 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        {expanded && (
          <div className="px-4 pb-4 space-y-3 border-t border-white/5">

            {/* ── Risk Score Gauge ──────────────────────────────────── */}
            <div className="pt-3">
              <div className="flex justify-between items-end mb-1.5">
                <span className="text-[0.55rem] font-mono tracking-[0.15em] uppercase text-gray-500">
                  Risk Score
                </span>
                <span className={`text-2xl font-bold font-mono tabular-nums ${risk.color}`}>
                  {riskScore !== null ? `${(riskScore * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 bg-[#1a1b2e] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${
                    riskScore > 0.7 ? 'bg-gradient-to-r from-red-600 to-red-400' :
                    riskScore > 0.4 ? 'bg-gradient-to-r from-amber-600 to-amber-400' :
                    'bg-gradient-to-r from-emerald-600 to-emerald-400'
                  }`}
                  style={{ width: `${(riskScore ?? 0) * 100}%` }}
                />
              </div>
            </div>

            {/* ── Weather Stats ─────────────────────────────────────── */}
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-[#0f1020] border border-white/5 rounded-lg p-2.5">
                <div className="text-[0.5rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-0.5">
                  Precipitation
                </div>
                <div className="text-sm font-bold font-mono text-cyan-400">
                  {data?.weather?.precipitation_mm !== undefined
                    ? `${data.weather.precipitation_mm.toFixed(1)} mm`
                    : '—'}
                </div>
              </div>
              <div className="bg-[#0f1020] border border-white/5 rounded-lg p-2.5">
                <div className="text-[0.5rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-0.5">
                  Wind Speed
                </div>
                <div className="text-sm font-bold font-mono text-cyan-400">
                  {data?.weather?.wind_speed_kmh !== undefined
                    ? `${data.weather.wind_speed_kmh.toFixed(1)} km/h`
                    : '—'}
                </div>
              </div>
            </div>

            {/* ── Gemini Alert Box ──────────────────────────────────── */}
            <div className="bg-black/50 border border-white/5 rounded-lg p-3 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-blue-500/40 to-transparent" />
              <div className="text-[0.5rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-1.5 flex items-center gap-1.5">
                <span className="inline-block w-1 h-1 rounded-full bg-blue-400" />
                Gemini Intelligence
              </div>
              {data?.gemini_alert ? (
                <p className="text-[0.7rem] leading-relaxed text-gray-300 font-mono">
                  {data.gemini_alert}
                </p>
              ) : (
                <p className="text-[0.7rem] text-gray-600 italic animate-pulse">
                  Monitoring environment...
                </p>
              )}
            </div>

            {/* ── City Scan Buttons ─────────────────────────────────── */}
            <div className="flex gap-1.5">
              {SCENARIOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => fetchDisruption(s)}
                  disabled={loading}
                  className={`flex-1 py-1.5 text-[0.55rem] font-bold tracking-wider uppercase rounded-md border transition-all ${
                    data?.city === s.city
                      ? 'bg-blue-500/15 border-blue-500/40 text-blue-400'
                      : 'bg-transparent border-white/5 text-gray-500 hover:text-gray-300 hover:border-white/15'
                  } ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer active:scale-95'}`}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* ── Timestamp ─────────────────────────────────────────── */}
            {lastUpdated && (
              <div className="text-[0.5rem] font-mono text-gray-600 text-center tracking-widest">
                Last scan: {lastUpdated.toLocaleTimeString()} · {data?.firebase || 'N/A'} mode
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
