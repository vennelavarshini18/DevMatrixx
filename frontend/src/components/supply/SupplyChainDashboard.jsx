import React, { useState, useCallback } from 'react';
import useSupplyChainData from '../../hooks/useSupplyChainData';
import SupplyMap from './SupplyMap';
import DisruptionCard from '../DisruptionCard';

const P2_API = 'http://localhost:8000';

/**
 * WareFlow Supply Chain Dashboard
 * 
 * Full-screen dark dashboard with:
 * - Left: Custom SVG network map (8 cities, animated route, truck position)
 * - Right: Shipment status, P2 disruption intel, route info, warehouse queues, demo controls
 * - Bottom overlay: Gemini alert card (slides in when risk > 0.7)
 */
export default function SupplyChainDashboard({ onBack }) {
  const {
    shipment, graphInfo, queues, loading, error, serverOnline,
    triggerWeatherEvent, startSimulation, stopSimulation, resetShipment,
  } = useSupplyChainData();

  const [demoLoading, setDemoLoading] = useState(null);
  const [p2Data, setP2Data] = useState(null);
  const [p2Loading, setP2Loading] = useState(false);

  // Fetch live disruption data from P2's endpoint
  const scanCity = useCallback(async (city, lat, lng) => {
    setP2Loading(true);
    try {
      const res = await fetch(`${P2_API}/api/supply/trigger-weather-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng, city, base_travel_time: 4.0, source: 'Lucknow', destination: 'Delhi' }),
      });
      const data = await res.json();
      setP2Data(data);
    } catch (err) {
      console.error('[P2 Scan] Failed:', err);
    } finally {
      setP2Loading(false);
    }
  }, []);

  // --- Risk score color logic ---
  const riskScore = shipment?.risk_score || 0;
  const riskColor = riskScore > 0.7 ? 'text-red-400' : riskScore > 0.3 ? 'text-amber-400' : 'text-emerald-400';
  const riskBg = riskScore > 0.7 ? 'bg-red-500/20 border-red-500/40' : riskScore > 0.3 ? 'bg-amber-500/20 border-amber-500/40' : 'bg-emerald-500/20 border-emerald-500/40';
  const riskLabel = riskScore > 0.7 ? 'HIGH' : riskScore > 0.3 ? 'MEDIUM' : 'LOW';

  // --- Status display ---
  const statusConfig = {
    in_transit: { label: 'In Transit', color: 'text-blue-400', dot: 'bg-blue-400' },
    rerouting: { label: 'Rerouting', color: 'text-amber-400 animate-pulse', dot: 'bg-amber-400' },
    delivered: { label: 'Delivered', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  };
  const sc = statusConfig[shipment?.status] || statusConfig.in_transit;

  // --- Demo action handlers ---
  const handleAction = useCallback(async (actionName, actionFn) => {
    setDemoLoading(actionName);
    try { await actionFn(); }
    catch (e) { console.error(e); }
    finally { setTimeout(() => setDemoLoading(null), 500); }
  }, []);

  // --- Loading state ---
  if (loading && !shipment) {
    return (
      <div className="w-screen h-screen bg-[#050505] flex flex-col items-center justify-center text-gray-400 font-mono">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" />
        <span className="text-sm tracking-[0.2em] uppercase animate-pulse">
          {error || 'Connecting to Supply Chain Server...'}
        </span>
        {error && (
          <p className="text-xs text-gray-600 mt-2">
            Run: <code className="text-gray-500">cd backend && python run_supply_server.py</code>
          </p>
        )}
        {onBack && (
          <button onClick={onBack} className="mt-6 px-4 py-2 text-sm border border-white/10 rounded-lg text-gray-500 hover:text-white hover:border-white/30 transition-all">
            ← Back
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="w-screen h-screen bg-[#050505] text-gray-200 overflow-hidden flex flex-col font-sans selection:bg-blue-900 selection:text-blue-100">

      {/* ── HEADER BAR ──────────────────────────────────────────────── */}
      <header className="flex-shrink-0 h-14 border-b border-white/5 bg-[#0a0a12]/90 backdrop-blur-md flex items-center justify-between px-6 z-20">
        <div className="flex items-center gap-4">
          {onBack && (
            <button onClick={onBack}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold tracking-wider uppercase text-gray-500 hover:text-white border border-white/10 hover:border-white/25 rounded-lg transition-all"
            >
              <span>←</span> Warehouse
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-gradient-to-tr from-blue-400 to-indigo-400 rounded-full shadow-[0_0_8px_rgba(96,165,250,0.5)]" />
            <span className="text-sm font-black tracking-tight text-white">WAREFLOW</span>
            <span className="text-[0.6rem] font-mono tracking-[0.2em] uppercase text-gray-600 ml-1">Supply Chain Intelligence</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[0.65rem] font-mono ${serverOnline ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${serverOnline ? 'bg-emerald-400' : 'bg-red-400'} ${serverOnline ? 'animate-pulse' : ''}`} />
            {serverOnline ? 'LIVE' : 'OFFLINE'}
          </div>
          <div className="text-[0.6rem] font-mono text-gray-600 tracking-wider">
            PORT 8001
          </div>
        </div>
      </header>

      {/* ── MAIN CONTENT ────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── LEFT: NETWORK MAP ─────────────────────────────────────── */}
        <div className="flex-1 p-3 min-w-0">
          <SupplyMap shipment={shipment} />
        </div>

        {/* ── RIGHT: SIDEBAR PANELS ─────────────────────────────────── */}
        <div className="w-[320px] flex-shrink-0 overflow-y-auto border-l border-white/5 bg-[#080810]/50 p-4 flex flex-col gap-3">

          {/* ── SHIPMENT STATUS ──────── */}
          <Panel title="ACTIVE SHIPMENT">
            <Row label="Order ID" value={shipment?.order_id || '—'} mono />
            <Row label="Status">
              <span className={`flex items-center gap-1.5 ${sc.color}`}>
                <span className={`w-2 h-2 rounded-full ${sc.dot}`} />
                {sc.label}
              </span>
            </Row>
            <Row label="ETA" value={`${shipment?.eta_hours || '—'} hours`} accent />
            <Row label="Risk Score">
              <span className={`inline-flex items-center gap-2 px-2 py-0.5 rounded-full text-xs font-bold border ${riskBg} ${riskColor}`}>
                {(riskScore * 100).toFixed(0)}% — {riskLabel}
              </span>
            </Row>
            {shipment?.weather && (
              <>
                <div className="border-t border-white/5 my-2 pt-2 text-[0.6rem] font-mono tracking-widest text-gray-500 uppercase">
                  Weather Intel
                </div>
                <Row label="Precipitation" value={`${shipment.weather.precipitation_mm?.toFixed(1) || '0.0'} mm`} mono />
                <Row label="Wind Speed" value={`${shipment.weather.wind_speed_kmh?.toFixed(1) || '0.0'} km/h`} mono />
              </>
            )}
          </Panel>

          {/* ── ROUTE ────────────────── */}
          <Panel title="ROUTE">
            <div className="flex flex-col gap-0.5 ml-1">
              {(shipment?.current_route || []).map((city, idx, arr) => {
                const isCurrent = city === shipment?.position;
                const isPast = arr.indexOf(shipment?.position) > idx;
                return (
                  <div key={city} className="flex items-center gap-2">
                    <div className="flex flex-col items-center w-4">
                      <div className={`w-2.5 h-2.5 rounded-full border-2 transition-all ${
                        isCurrent ? 'bg-blue-400 border-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.6)]' :
                        isPast ? 'bg-gray-600 border-gray-600' :
                        'bg-transparent border-gray-600'
                      }`} />
                      {idx < arr.length - 1 && (
                        <div className={`w-0.5 h-4 ${isPast ? 'bg-gray-600' : 'bg-gray-700/50'}`} />
                      )}
                    </div>
                    <span className={`text-xs font-mono tracking-wide ${
                      isCurrent ? 'text-blue-400 font-bold' : isPast ? 'text-gray-600' : 'text-gray-400'
                    }`}>
                      {city} {isCurrent && '← TRUCK'}
                    </span>
                  </div>
                );
              })}
            </div>
          </Panel>

          {/* ── WAREHOUSE QUEUES ─────── */}
          <Panel title={`WAREHOUSE QUEUES (${Object.keys(queues).length})`}>
            <div className="grid grid-cols-2 gap-1.5 max-h-[220px] overflow-y-auto pr-1">
              {Object.entries(queues).map(([whId, pending]) => (
                <div key={whId} className="bg-[#0f1020] border border-white/5 rounded-lg p-2 text-center">
                  <div className="text-[0.5rem] font-mono tracking-[0.12em] uppercase text-gray-500 mb-0.5">{whId}</div>
                  <div className={`text-lg font-bold font-mono ${pending > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {pending}
                  </div>
                  <div className="text-[0.45rem] text-gray-600">pending</div>
                </div>
              ))}
              {Object.keys(queues).length === 0 && (
                <div className="col-span-2 text-xs text-gray-600 text-center py-2">No queue data</div>
              )}
            </div>
          </Panel>

          {/* ── DISRUPTION INTEL ────── */}
          <DisruptionCard />

          {/* ── GEMINI ALERT ────────── */}
          {shipment?.gemini_alert && (
            <div className="bg-red-950/40 border border-red-500/30 rounded-lg p-3 relative overflow-hidden flex-shrink-0 animate-[fadeIn_0.3s_ease-out]">
              <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-red-500/40 to-transparent" />
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm">⚠️</span>
                <span className="text-[0.6rem] font-bold text-red-400 tracking-wide uppercase">Weather Alert</span>
              </div>
              <p className="text-[0.65rem] text-gray-300 leading-relaxed font-mono">
                {shipment.gemini_alert}
              </p>
            </div>
          )}

          {/* ── DEMO CONTROLS ───────── */}
          <Panel title="DEMO CONTROLS">
            <div className="flex flex-col gap-2">
              <DemoButton
                label="Start Simulation"
                icon="🚛"
                loading={demoLoading === 'sim'}
                onClick={() => handleAction('sim', startSimulation)}
                color="blue"
              />
              <DemoButton
                label="Trigger Storm"
                icon="⛈️"
                sublabel="Agra–Delhi highway"
                loading={demoLoading === 'storm'}
                onClick={() => handleAction('storm', triggerWeatherEvent)}
                color="red"
              />
              <DemoButton
                label="Reset Shipment"
                icon="↺"
                loading={demoLoading === 'reset'}
                onClick={() => handleAction('reset', resetShipment)}
                color="gray"
              />
            </div>
          </Panel>

          {/* ── GRAPH STATS ──────────── */}
          {graphInfo && (
            <div className="text-[0.6rem] font-mono text-gray-600 text-center tracking-widest uppercase mt-auto pt-2 border-t border-white/5">
              {graphInfo.total_cities} Cities · {graphInfo.total_highways} Highways · {graphInfo.total_warehouses || 10} WH · Dijkstra
            </div>
          )}
        </div>
      </div>

    </div>
  );
}


// ─── REUSABLE SUB-COMPONENTS ────────────────────────────────────────────────

function Panel({ title, children }) {
  return (
    <div className="bg-[#0a0b14]/80 border border-white/5 rounded-xl p-3 backdrop-blur-sm">
      <h3 className="text-[0.6rem] font-bold tracking-[0.2em] uppercase text-gray-500 mb-2.5 pb-1.5 border-b border-white/5">
        {title}
      </h3>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
}

function Row({ label, value, mono, accent, children }) {
  return (
    <div className="flex justify-between items-center text-xs">
      <span className="text-gray-500">{label}</span>
      {children || (
        <span className={`${mono ? 'font-mono' : ''} ${accent ? 'text-blue-400 font-semibold' : 'text-gray-300'}`}>
          {value}
        </span>
      )}
    </div>
  );
}

function DemoButton({ label, icon, sublabel, loading, onClick, color }) {
  const colors = {
    blue: 'border-blue-500/30 hover:border-blue-400/60 hover:bg-blue-950/30 text-blue-400',
    red: 'border-red-500/30 hover:border-red-400/60 hover:bg-red-950/30 text-red-400',
    gray: 'border-gray-600/30 hover:border-gray-500/60 hover:bg-gray-900/30 text-gray-400',
  };
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-sm font-medium transition-all ${colors[color]} ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer active:scale-[0.98]'}`}
    >
      <span className="text-base">{loading ? '⏳' : icon}</span>
      <div className="flex flex-col items-start">
        <span className="text-xs font-semibold tracking-wide">{label}</span>
        {sublabel && <span className="text-[0.55rem] text-gray-600 font-mono">{sublabel}</span>}
      </div>
    </button>
  );
}
