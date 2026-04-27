import React, { useMemo } from 'react';
import DisruptionCard from '../DisruptionCard';

/**
 * Custom SVG-based network map of the Indian highway system.
 * 
 * Shows 8 cities as nodes, 12 highway edges, the active route as a 
 * glowing animated polyline, and the truck position as a pulsing dot.
 * 
 * This is deliberately NOT a Google Maps embed — it's a custom dark-themed
 * network visualization that looks far more premium for hackathon demos.
 */

// ─── CITY POSITIONS (geo-accurate, scaled to 800x500 SVG viewport) ─────────
const CITY_POS = {
  Lucknow:   { x: 513, y: 262 },
  Kanpur:    { x: 464, y: 294 },
  Agra:      { x: 284, y: 236 },
  Delhi:     { x: 222, y: 121 },
  Jaipur:    { x: 111, y: 257 },
  Varanasi:  { x: 670, y: 384 },
  Prayagraj: { x: 583, y: 375 },
  Gwalior:   { x: 297, y: 312 },
};

// ─── ALL HIGHWAY EDGES (must match graph_engine.py exactly) ────────────────
const ALL_EDGES = [
  ['Lucknow', 'Kanpur'],
  ['Lucknow', 'Agra'],
  ['Lucknow', 'Prayagraj'],
  ['Kanpur', 'Agra'],
  ['Kanpur', 'Prayagraj'],
  ['Kanpur', 'Delhi'],
  ['Agra', 'Delhi'],
  ['Agra', 'Gwalior'],
  ['Agra', 'Jaipur'],
  ['Gwalior', 'Delhi'],
  ['Delhi', 'Jaipur'],
  ['Prayagraj', 'Varanasi'],
];

// Warehouse cities get a special indicator
const WAREHOUSE_CITIES = ['Lucknow', 'Delhi'];

export default function SupplyMap({ shipment }) {
  const currentRoute = shipment?.current_route || [];
  const truckCity = shipment?.position || null;
  const riskScore = shipment?.risk_score || 0;

  // Build the active route path as SVG points
  const routePath = useMemo(() => {
    return currentRoute
      .filter(city => CITY_POS[city])
      .map(city => CITY_POS[city]);
  }, [currentRoute]);

  // Build SVG polyline points string
  const routePointsStr = routePath.map(p => `${p.x},${p.y}`).join(' ');

  // Cities on the active route (for highlighting)
  const routeSet = useMemo(() => new Set(currentRoute), [currentRoute]);

  // Truck SVG position
  const truckPos = truckCity && CITY_POS[truckCity] ? CITY_POS[truckCity] : null;

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden bg-[#06080f] border border-white/5">
      {/* Ambient background glows */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[20%] left-[30%] w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[100px]" />
        <div className="absolute bottom-[20%] right-[20%] w-[250px] h-[250px] bg-indigo-500/5 rounded-full blur-[100px]" />
      </div>

      <svg viewBox="0 0 800 500" className="w-full h-full" style={{ filter: 'drop-shadow(0 0 2px rgba(59,130,246,0.1))' }}>
        <defs>
          {/* Route glow filter */}
          <filter id="routeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Truck pulse glow */}
          <filter id="truckGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* City node glow */}
          <filter id="cityGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Animated dash for route */}
          <style>{`
            @keyframes dashFlow {
              to { stroke-dashoffset: -40; }
            }
            @keyframes truckPulse {
              0%, 100% { r: 8; opacity: 1; }
              50% { r: 12; opacity: 0.7; }
            }
            @keyframes truckRing {
              0% { r: 12; opacity: 0.6; }
              100% { r: 28; opacity: 0; }
            }
          `}</style>
        </defs>

        {/* ── BACKGROUND GRID ──────────────────────────────────── */}
        {Array.from({ length: 20 }, (_, i) => (
          <line key={`gv${i}`} x1={i * 40 + 20} y1="0" x2={i * 40 + 20} y2="500"
            stroke="#ffffff" strokeWidth="0.3" opacity="0.03" />
        ))}
        {Array.from({ length: 13 }, (_, i) => (
          <line key={`gh${i}`} x1="0" y1={i * 40 + 20} x2="800" y2={i * 40 + 20}
            stroke="#ffffff" strokeWidth="0.3" opacity="0.03" />
        ))}

        {/* ── ALL HIGHWAY EDGES (background) ───────────────────── */}
        {ALL_EDGES.map(([a, b], idx) => {
          const pa = CITY_POS[a];
          const pb = CITY_POS[b];
          if (!pa || !pb) return null;
          return (
            <line key={`edge-${idx}`}
              x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
              stroke="#1e293b" strokeWidth="1.5" strokeLinecap="round"
              opacity="0.6"
            />
          );
        })}

        {/* ── ACTIVE ROUTE (glowing blue polyline) ─────────────── */}
        {routePath.length > 1 && (
          <>
            {/* Outer glow */}
            <polyline
              points={routePointsStr}
              fill="none"
              stroke={riskScore > 0.7 ? '#f59e0b' : '#3b82f6'}
              strokeWidth="6"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.3"
              filter="url(#routeGlow)"
            />
            {/* Core line */}
            <polyline
              points={routePointsStr}
              fill="none"
              stroke={riskScore > 0.7 ? '#f59e0b' : '#60a5fa'}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Animated dash overlay */}
            <polyline
              points={routePointsStr}
              fill="none"
              stroke="#ffffff"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="8 32"
              opacity="0.4"
              style={{ animation: 'dashFlow 1.5s linear infinite' }}
            />
          </>
        )}

        {/* ── CITY NODES ───────────────────────────────────────── */}
        {Object.entries(CITY_POS).map(([name, pos]) => {
          const isOnRoute = routeSet.has(name);
          const isWarehouse = WAREHOUSE_CITIES.includes(name);
          const isTruckHere = name === truckCity;

          return (
            <g key={name}>
              {/* Warehouse indicator ring */}
              {isWarehouse && (
                <circle cx={pos.x} cy={pos.y} r="14"
                  fill="none"
                  stroke={isOnRoute ? '#60a5fa' : '#475569'}
                  strokeWidth="1"
                  strokeDasharray="3 3"
                  opacity="0.5"
                />
              )}

              {/* City dot */}
              <circle cx={pos.x} cy={pos.y}
                r={isWarehouse ? 6 : 4}
                fill={isTruckHere ? '#60a5fa' : isOnRoute ? '#93c5fd' : '#475569'}
                filter={isOnRoute ? 'url(#cityGlow)' : undefined}
              />

              {/* City label */}
              <text x={pos.x} y={pos.y - (isWarehouse ? 20 : 14)}
                fill={isOnRoute ? '#e2e8f0' : '#64748b'}
                fontSize={isWarehouse ? '11' : '9'}
                fontFamily="system-ui, sans-serif"
                fontWeight={isOnRoute ? '600' : '400'}
                textAnchor="middle"
                letterSpacing="0.5"
              >
                {name}
              </text>

              {/* Warehouse label */}
              {isWarehouse && (
                <text x={pos.x} y={pos.y + 24}
                  fill="#64748b" fontSize="7" fontFamily="monospace"
                  textAnchor="middle" letterSpacing="1.5"
                >
                  WAREHOUSE
                </text>
              )}
            </g>
          );
        })}

        {/* ── TRUCK MARKER (animated pulsing dot) ──────────────── */}
        {truckPos && (
          <g>
            {/* Expanding ripple ring */}
            <circle cx={truckPos.x} cy={truckPos.y}
              fill="none" stroke="#3b82f6" strokeWidth="2"
              style={{ animation: 'truckRing 2s ease-out infinite' }}
            />
            {/* Outer glow */}
            <circle cx={truckPos.x} cy={truckPos.y} r="10"
              fill="#3b82f6" opacity="0.2" filter="url(#truckGlow)"
            />
            {/* Core truck dot */}
            <circle cx={truckPos.x} cy={truckPos.y}
              fill="#60a5fa" stroke="#ffffff" strokeWidth="2"
              style={{ animation: 'truckPulse 2s ease-in-out infinite' }}
            />
            {/* Truck emoji */}
            <text x={truckPos.x} y={truckPos.y + 4}
              fontSize="14" textAnchor="middle" style={{ pointerEvents: 'none' }}
            >
              🚛
            </text>
          </g>
        )}

        {/* ── MAP LEGEND ───────────────────────────────────────── */}
        <g transform="translate(20, 460)">
          <rect x="0" y="-10" width="180" height="35" rx="6" fill="#0f172a" opacity="0.7" />
          <circle cx="15" cy="5" r="3" fill="#475569" />
          <text x="25" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">City Hub</text>
          <line x1="70" y1="5" x2="90" y2="5" stroke="#60a5fa" strokeWidth="2" />
          <text x="95" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">Active Route</text>
          <text x="155" y="9" fill="#64748b" fontSize="10">🚛</text>
          <text x="165" y="9" fill="#64748b" fontSize="8" fontFamily="monospace"></text>
        </g>
      </svg>
      
      {/* ── DISRUPTION HUD ─────────────────────────────────────── */}
      <DisruptionCard />
    </div>
  );
}
