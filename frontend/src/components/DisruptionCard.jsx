import React, { useEffect, useState, useRef, useCallback } from 'react';

/**
 * DisruptionCard — Person 2's Disruption Intelligence Widget
 *
 * Route-aware: receives the active shipment and scans cities on the ACTUAL
 * active route via P2's LightGBM model (port 8000).
 *
 * Features:
 * - Auto-scans intermediate route cities on mount and when route changes
 * - Periodic re-scan every 30 seconds
 * - Dynamic city buttons from the active shipment route
 * - Real weather data → LightGBM prediction → Gemini alert
 */

const BACKEND_URL = 'http://localhost:8000';

// Full city coordinates for P2 weather lookups
const CITY_GEO = {
  Lucknow:       { lat: 26.8467, lng: 80.9462 },
  Agra:          { lat: 27.1767, lng: 78.0081 },
  Delhi:         { lat: 28.6139, lng: 77.2090 },
  Kanpur:        { lat: 26.4499, lng: 80.3319 },
  Jaipur:        { lat: 26.9124, lng: 75.7873 },
  Gwalior:       { lat: 26.2183, lng: 78.1828 },
  Varanasi:      { lat: 25.3176, lng: 82.9739 },
  Prayagraj:     { lat: 25.4358, lng: 81.8463 },
  Patna:         { lat: 25.6093, lng: 85.1376 },
  Bhopal:        { lat: 23.2599, lng: 77.4126 },
  Indore:        { lat: 22.7196, lng: 75.8577 },
  Nagpur:        { lat: 21.1458, lng: 79.0882 },
  Mumbai:        { lat: 19.0760, lng: 72.8777 },
  Pune:          { lat: 18.5204, lng: 73.8567 },
  Hyderabad:     { lat: 17.3850, lng: 78.4867 },
  Bangalore:     { lat: 12.9716, lng: 77.5946 },
  Chennai:       { lat: 13.0827, lng: 80.2707 },
  Kolkata:       { lat: 22.5726, lng: 88.3639 },
  Ahmedabad:     { lat: 23.0225, lng: 72.5714 },
  Surat:         { lat: 21.1702, lng: 72.8311 },
  Nashik:        { lat: 19.9975, lng: 73.7898 },
  Visakhapatnam: { lat: 17.6868, lng: 83.2185 },
};

export default function DisruptionCard({ shipment }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [activeCity, setActiveCity] = useState(null);
  const lastRouteRef = useRef(null);

  // Derive route info from the shipment
  const route = shipment?.current_route || [];
  const source = route[0] || 'Lucknow';
  const destination = route[route.length - 1] || 'Delhi';

  // Build dynamic scan buttons from route cities
  const routeCities = route.filter(city => CITY_GEO[city]);

  // Fetch disruption data for a given city using P2's LightGBM model
  const fetchDisruption = useCallback(async (cityName) => {
    const geo = CITY_GEO[cityName];
    if (!geo) {
      console.warn(`[P2 DisruptionCard] No coordinates for ${cityName}`);
      return;
    }

    setLoading(true);
    setActiveCity(cityName);
    try {
      const res = await fetch(`${BACKEND_URL}/api/supply/trigger-weather-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: geo.lat,
          lng: geo.lng,
          city: cityName,
          base_travel_time: 4.0,
          source,
          destination,
        }),
      });
      const result = await res.json();
      setData(result);
      setLastUpdated(new Date());

      // Sync clear conditions back to P3 (port 8001) so Active Shipment matches
      if (result.risk_score <= 0.7) {
        try {
          await fetch(`http://localhost:8001/supply/trigger-weather-event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              edge_a: cityName,
              edge_b: destination,
              risk_score: result.risk_score,
              gemini_alert: result.gemini_alert || `All clear at ${cityName}. Risk: ${(result.risk_score * 100).toFixed(0)}%.`,
            }),
          });
        } catch (err) {
          console.warn('[P2 DisruptionCard] Failed to sync with P3:', err);
        }
      }

    } catch (err) {
      console.error('[P2 DisruptionCard] Fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [source, destination]);

  // Auto-scan: when route changes, scan the first intermediate city (or source)
  useEffect(() => {
    const routeKey = route.join(',');
    if (routeKey === lastRouteRef.current) return; // no change
    lastRouteRef.current = routeKey;

    if (route.length === 0) return;

    if (shipment?.risk_score > 0.7) {
      console.log('[P2 DisruptionCard] Active disruption detected. Skipping auto-scan to preserve state.');
      return;
    }

    // Pick the best city to auto-scan:
    // Prefer intermediate cities (where disruption matters most),
    // then the truck's current position, then the source
    const truckCity = shipment?.position;
    let scanTarget;

    if (route.length >= 3) {
      // Scan the city just ahead of the truck (or first intermediate)
      const truckIdx = truckCity ? route.indexOf(truckCity) : 0;
      const nextIdx = Math.min(truckIdx + 1, route.length - 2);
      scanTarget = route[nextIdx];
    } else {
      scanTarget = truckCity || route[0];
    }

    if (CITY_GEO[scanTarget]) {
      console.log(`[P2 DisruptionCard] Route changed → auto-scanning: ${scanTarget}`);
      fetchDisruption(scanTarget);
    }
  }, [route, shipment?.position, shipment?.risk_score, fetchDisruption]);

  // Periodic re-scan every 30s on the current active city
  useEffect(() => {
    if (!activeCity) return;
    const interval = setInterval(() => {
      console.log(`[P2 DisruptionCard] Periodic re-scan: ${activeCity}`);
      fetchDisruption(activeCity);
    }, 30000);
    return () => clearInterval(interval);
  }, [activeCity, fetchDisruption]);

  // Risk UI helpers
  const isDisrupted = shipment?.risk_score > 0.7;
  const riskScore = isDisrupted ? shipment.risk_score : (data?.risk_score ?? shipment?.risk_score ?? null);
  const displayGemini = isDisrupted ? shipment.gemini_alert : (data?.gemini_alert ?? shipment?.gemini_alert);
  
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
            {activeCity && (
              <span className="text-[0.5rem] font-mono text-blue-400/60 tracking-wide">
                · {activeCity}
              </span>
            )}
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

            {/* ── Scanning Target ──────────────────────────────────────── */}
            <div className="pt-2 flex items-center gap-2">
              <span className="text-[0.5rem] font-mono tracking-[0.15em] uppercase text-gray-600">
                Scanning
              </span>
              <span className="text-[0.65rem] font-bold text-blue-400 font-mono">
                {activeCity || '—'}
              </span>
              <span className="text-[0.5rem] text-gray-600 font-mono">
                on {source} → {destination} route
              </span>
            </div>

            {/* ── Risk Score Gauge ──────────────────────────────────── */}
            <div className="pt-1">
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

            {/* ── Environment Stats ─────────────────────────────────────── */}
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-[#0f1020] border border-white/5 rounded-lg p-2.5">
                <div className="text-[0.45rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-0.5">
                  Precipitation
                </div>
                <div className="text-xs font-bold font-mono text-cyan-400">
                  {data?.weather?.precipitation_mm !== undefined
                    ? `${data.weather.precipitation_mm.toFixed(1)} mm`
                    : '—'}
                </div>
              </div>
              <div className="bg-[#0f1020] border border-white/5 rounded-lg p-2.5">
                <div className="text-[0.45rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-0.5">
                  Wind Speed
                </div>
                <div className="text-xs font-bold font-mono text-cyan-400">
                  {data?.weather?.wind_speed_kmh !== undefined
                    ? `${data.weather.wind_speed_kmh.toFixed(1)} km/h`
                    : '—'}
                </div>
              </div>
              <div className="bg-[#0f1020] border border-white/5 rounded-lg p-2.5">
                <div className="text-[0.45rem] font-mono tracking-[0.15em] uppercase text-gray-600 mb-0.5">
                  Traffic
                </div>
                <div className={`text-xs font-bold font-mono ${
                  !data?.traffic?.congestion_ratio ? 'text-gray-500' :
                  data.traffic.congestion_ratio > 2.0 ? 'text-red-400' :
                  data.traffic.congestion_ratio > 1.3 ? 'text-amber-400' :
                  'text-emerald-400'
                }`}>
                  {data?.traffic?.congestion_ratio !== undefined
                    ? `${data.traffic.congestion_ratio.toFixed(1)}x`
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
              {displayGemini ? (
                <p className="text-[0.7rem] leading-relaxed text-gray-300 font-mono">
                  {displayGemini}
                </p>
              ) : (
                <p className="text-[0.7rem] text-gray-600 italic animate-pulse">
                  Monitoring environment...
                </p>
              )}
            </div>

            {/* ── Route City Scan Buttons ─────────────────────────────── */}
            <div className="flex flex-wrap gap-1.5">
              {routeCities.length > 0 ? (
                routeCities.map((city) => (
                  <button
                    key={city}
                    onClick={() => fetchDisruption(city)}
                    disabled={loading}
                    className={`px-2 py-1.5 text-[0.55rem] font-bold tracking-wider uppercase rounded-md border transition-all ${
                      activeCity === city
                        ? 'bg-blue-500/15 border-blue-500/40 text-blue-400'
                        : 'bg-transparent border-white/5 text-gray-500 hover:text-gray-300 hover:border-white/15'
                    } ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer active:scale-95'}`}
                  >
                    {city}
                  </button>
                ))
              ) : (
                // Fallback: show some default cities if no active route
                ['Lucknow', 'Delhi', 'Mumbai', 'Bangalore'].map((city) => (
                  <button
                    key={city}
                    onClick={() => fetchDisruption(city)}
                    disabled={loading}
                    className={`flex-1 py-1.5 text-[0.55rem] font-bold tracking-wider uppercase rounded-md border transition-all ${
                      activeCity === city
                        ? 'bg-blue-500/15 border-blue-500/40 text-blue-400'
                        : 'bg-transparent border-white/5 text-gray-500 hover:text-gray-300 hover:border-white/15'
                    } ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer active:scale-95'}`}
                  >
                    {city}
                  </button>
                ))
              )}
            </div>

            {/* ── Timestamp ─────────────────────────────────────────── */}
            {lastUpdated && (
              <div className="text-[0.5rem] font-mono text-gray-600 text-center tracking-widest">
                Last scan: {lastUpdated.toLocaleTimeString()} · {data?.firebase || 'N/A'} mode · LightGBM
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
