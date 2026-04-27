import React, { useMemo } from 'react';
import DisruptionCard from '../DisruptionCard';

/**
 * Custom SVG-based network map of the Indian highway system.
 * 
 * Shows 22 cities as nodes, 50+ highway edges, the active route as a 
 * glowing animated polyline, and the truck position as a pulsing dot.
 * 10 warehouse cities are highlighted distinctly.
 */

// ─── CITY POSITIONS (geo-accurate, scaled to 900x700 SVG viewport) ─────────
// Mapped from real lat/lng to SVG coordinates
const CITY_POS = {
  // Warehouse cities (10)
  Delhi:         { x: 310, y: 95 },
  Mumbai:        { x: 145, y: 415 },
  Bangalore:     { x: 330, y: 600 },
  Hyderabad:     { x: 350, y: 480 },
  Chennai:       { x: 440, y: 580 },
  Kolkata:       { x: 690, y: 310 },
  Lucknow:       { x: 455, y: 175 },
  Jaipur:        { x: 190, y: 190 },
  Ahmedabad:     { x: 115, y: 310 },
  Pune:          { x: 180, y: 470 },
  // Transit cities (12)
  Agra:          { x: 325, y: 170 },
  Kanpur:        { x: 430, y: 210 },
  Varanasi:      { x: 555, y: 250 },
  Prayagraj:     { x: 510, y: 265 },
  Gwalior:       { x: 315, y: 225 },
  Nagpur:        { x: 375, y: 395 },
  Indore:        { x: 230, y: 330 },
  Bhopal:        { x: 295, y: 310 },
  Patna:         { x: 600, y: 210 },
  Surat:         { x: 130, y: 370 },
  Nashik:        { x: 160, y: 430 },
  Visakhapatnam: { x: 530, y: 460 },
};

// ─── ALL HIGHWAY EDGES (matches expanded graph_engine.py) ────────────────
const ALL_EDGES = [
  // Northern corridor
  ['Delhi', 'Agra'], ['Delhi', 'Jaipur'], ['Delhi', 'Lucknow'], ['Delhi', 'Gwalior'], ['Delhi', 'Kanpur'],
  // UP corridor  
  ['Lucknow', 'Kanpur'], ['Lucknow', 'Agra'], ['Lucknow', 'Prayagraj'], ['Lucknow', 'Varanasi'],
  ['Kanpur', 'Agra'], ['Kanpur', 'Prayagraj'], ['Prayagraj', 'Varanasi'], ['Varanasi', 'Patna'],
  // Agra
  ['Agra', 'Gwalior'], ['Agra', 'Jaipur'],
  // Central India
  ['Gwalior', 'Bhopal'], ['Bhopal', 'Indore'], ['Bhopal', 'Nagpur'],
  ['Indore', 'Ahmedabad'], ['Indore', 'Surat'], ['Nagpur', 'Hyderabad'], ['Nagpur', 'Pune'],
  // Western corridor
  ['Jaipur', 'Ahmedabad'], ['Ahmedabad', 'Surat'], ['Ahmedabad', 'Mumbai'],
  ['Surat', 'Mumbai'], ['Surat', 'Nashik'], ['Mumbai', 'Nashik'], ['Mumbai', 'Pune'], ['Nashik', 'Pune'],
  // Southern West
  ['Pune', 'Hyderabad'], ['Pune', 'Bangalore'], ['Mumbai', 'Hyderabad'],
  // Southern Central & East
  ['Hyderabad', 'Bangalore'], ['Hyderabad', 'Chennai'], ['Hyderabad', 'Visakhapatnam'],
  ['Bangalore', 'Chennai'],
  // Eastern corridor
  ['Kolkata', 'Patna'], ['Kolkata', 'Visakhapatnam'], ['Patna', 'Lucknow'], ['Visakhapatnam', 'Chennai'],
  // Cross-links
  ['Jaipur', 'Gwalior'], ['Nagpur', 'Indore'], ['Bhopal', 'Jaipur'], ['Kanpur', 'Gwalior'],
  ['Nagpur', 'Kolkata'], ['Patna', 'Varanasi'], ['Indore', 'Nashik'],
];

// Warehouse cities get special indicator
const WAREHOUSE_CITIES = [
  'Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Chennai',
  'Kolkata', 'Lucknow', 'Jaipur', 'Ahmedabad', 'Pune'
];

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
        <div className="absolute top-[15%] left-[25%] w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[100px]" />
        <div className="absolute bottom-[15%] right-[15%] w-[250px] h-[250px] bg-indigo-500/5 rounded-full blur-[100px]" />
        <div className="absolute top-[50%] left-[10%] w-[200px] h-[200px] bg-purple-500/3 rounded-full blur-[80px]" />
      </div>

      <svg viewBox="0 0 900 700" className="w-full h-full" style={{ filter: 'drop-shadow(0 0 2px rgba(59,130,246,0.1))' }}>
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
          {/* Warehouse glow */}
          <filter id="whGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur" />
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
            @keyframes warehousePulse {
              0%, 100% { opacity: 0.3; }
              50% { opacity: 0.6; }
            }
          `}</style>
        </defs>

        {/* ── BACKGROUND GRID ──────────────────────────────────── */}
        {Array.from({ length: 23 }, (_, i) => (
          <line key={`gv${i}`} x1={i * 40 + 20} y1="0" x2={i * 40 + 20} y2="700"
            stroke="#ffffff" strokeWidth="0.3" opacity="0.03" />
        ))}
        {Array.from({ length: 18 }, (_, i) => (
          <line key={`gh${i}`} x1="0" y1={i * 40 + 20} x2="900" y2={i * 40 + 20}
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
              stroke="#1e293b" strokeWidth="1.2" strokeLinecap="round"
              opacity="0.5"
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
                <>
                  <circle cx={pos.x} cy={pos.y} r="16"
                    fill="none"
                    stroke={isOnRoute ? '#60a5fa' : '#6366f1'}
                    strokeWidth="1"
                    strokeDasharray="3 3"
                    opacity="0.4"
                    style={{ animation: 'warehousePulse 3s ease-in-out infinite' }}
                  />
                  <circle cx={pos.x} cy={pos.y} r="10"
                    fill={isOnRoute ? '#3b82f620' : '#6366f115'}
                    stroke="none"
                  />
                </>
              )}

              {/* City dot */}
              <circle cx={pos.x} cy={pos.y}
                r={isWarehouse ? 5 : 3}
                fill={isTruckHere ? '#60a5fa' : isOnRoute ? '#93c5fd' : isWarehouse ? '#818cf8' : '#475569'}
                filter={isOnRoute ? 'url(#cityGlow)' : isWarehouse ? 'url(#whGlow)' : undefined}
              />

              {/* City label */}
              <text x={pos.x} y={pos.y - (isWarehouse ? 22 : 12)}
                fill={isOnRoute ? '#e2e8f0' : isWarehouse ? '#a5b4fc' : '#64748b'}
                fontSize={isWarehouse ? '10' : '8'}
                fontFamily="system-ui, sans-serif"
                fontWeight={isOnRoute ? '600' : isWarehouse ? '500' : '400'}
                textAnchor="middle"
                letterSpacing="0.5"
              >
                {name}
              </text>

              {/* Warehouse label */}
              {isWarehouse && (
                <text x={pos.x} y={pos.y + 22}
                  fill="#6366f1" fontSize="6" fontFamily="monospace"
                  textAnchor="middle" letterSpacing="1.2"
                  opacity="0.6"
                >
                  WH
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
        <g transform="translate(20, 660)">
          <rect x="0" y="-10" width="260" height="35" rx="6" fill="#0f172a" opacity="0.7" />
          <circle cx="15" cy="5" r="3" fill="#475569" />
          <text x="25" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">City</text>
          <circle cx="55" cy="5" r="4" fill="#818cf8" />
          <text x="65" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">Warehouse</text>
          <line x1="125" y1="5" x2="145" y2="5" stroke="#60a5fa" strokeWidth="2" />
          <text x="150" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">Route</text>
          <text x="185" y="9" fill="#64748b" fontSize="10">🚛</text>
          <text x="200" y="9" fill="#64748b" fontSize="8" fontFamily="monospace">Truck</text>
        </g>

        {/* City count label */}
        <text x="880" y="690" fill="#334155" fontSize="8" fontFamily="monospace" textAnchor="end">
          {Object.keys(CITY_POS).length} Cities · {ALL_EDGES.length} Highways · 10 Warehouses
        </text>
      </svg>
      
      {/* ── DISRUPTION HUD ─────────────────────────────────────── */}
      <DisruptionCard />
    </div>
  );
}
