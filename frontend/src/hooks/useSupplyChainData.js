import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8001';
const P2_API = 'http://localhost:8000';

// City coordinates for P2 weather checks
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

/**
 * Custom hook that polls the P3 Supply Chain FastAPI server for real-time data.
 * Uses HTTP polling (2s interval) — works out of the box with zero extra config.
 * 
 * Returns: shipment state, graph info, warehouse queues, active orders, and action functions.
 */
export default function useSupplyChainData() {
  const [shipment, setShipment] = useState(null);
  const [graphInfo, setGraphInfo] = useState(null);
  const [queues, setQueues] = useState({});
  const [activeOrders, setActiveOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [serverOnline, setServerOnline] = useState(false);

  // Fetch graph info once on mount (static data — cities + edges)
  useEffect(() => {
    fetch(`${API_BASE}/supply/graph-info`)
      .then(res => res.json())
      .then(data => {
        setGraphInfo(data);
        setServerOnline(true);
      })
      .catch(() => setError('Supply chain server offline (port 8001)'));
  }, []);

  // Poll shipment status every 2s
  useEffect(() => {
    const fetchShipment = () => {
      fetch(`${API_BASE}/supply/route-status`)
        .then(res => res.json())
        .then(data => {
          setShipment(data);
          setLoading(false);
          setError(null);
          setServerOnline(true);
        })
        .catch(() => {
          setError('Supply chain server offline');
          setServerOnline(false);
        });
    };

    fetchShipment();
    const interval = setInterval(fetchShipment, 2000);
    return () => clearInterval(interval);
  }, []);

  // Poll warehouse queues every 5s
  useEffect(() => {
    const fetchQueues = () => {
      fetch(`${API_BASE}/supply/warehouse-queues`)
        .then(res => res.json())
        .then(data => setQueues(data))
        .catch(() => {});
    };

    fetchQueues();
    const interval = setInterval(fetchQueues, 5000);
    return () => clearInterval(interval);
  }, []);

  // Poll active orders every 5s
  useEffect(() => {
    const fetchOrders = () => {
      fetch(`${API_BASE}/orders/active`)
        .then(res => res.json())
        .then(data => setActiveOrders(data.orders || []))
        .catch(() => {});
    };

    fetchOrders();
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  // --- Helper: make a POST request with full error logging ---
  const postAction = useCallback(async (endpoint, body = {}) => {
    const url = `${API_BASE}${endpoint}`;
    console.log(`[SupplyChain] POST ${url}`, body);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      console.log(`[SupplyChain] Response from ${endpoint}:`, data);
      if (!res.ok) {
        console.error(`[SupplyChain] HTTP ${res.status}:`, data);
      }
      return data;
    } catch (err) {
      console.error(`[SupplyChain] FAILED POST ${endpoint}:`, err);
      return { error: err.message };
    }
  }, []);

  // --- Action Functions (for demo controls) ---

  const triggerWeatherEvent = useCallback(
    async () => {
      // Pick a city from the current active route to scan via P2's ML model.
      // If no active route, pick a random city from the graph.
      const route = shipment?.current_route || [];
      let targetCity;
      if (route.length >= 3) {
        // Pick a random intermediate city (not source or destination)
        const intermediates = route.slice(1, -1);
        targetCity = intermediates[Math.floor(Math.random() * intermediates.length)];
      } else if (route.length > 0) {
        targetCity = route[Math.floor(Math.random() * route.length)];
      } else {
        // Fallback: random from all cities
        const allCities = Object.keys(CITY_GEO);
        targetCity = allCities[Math.floor(Math.random() * allCities.length)];
      }

      const geo = CITY_GEO[targetCity];
      if (!geo) {
        console.warn(`[SupplyChain] No coordinates for ${targetCity}, falling back`);
        return postAction('/supply/trigger-weather-event', { edge_a: targetCity, edge_b: 'Delhi', risk_score: 0.85 });
      }

      const source = route[0] || 'Lucknow';
      const destination = route[route.length - 1] || 'Delhi';

      // Simulate severe storm weather for the demo:
      // Heavy precipitation (65-78mm) and high wind (75-95 km/h)
      // These are sent as overrides to P2's API so LightGBM processes realistic
      // storm-level inputs and produces a high risk score through the real ML pipeline.
      const stormPrecip = 65 + Math.random() * 13;   // 65-78 mm
      const stormWind = 75 + Math.random() * 20;     // 75-95 km/h

      console.log(`[SupplyChain] Simulating storm at ${targetCity} via P2 ML model...`);
      console.log(`[SupplyChain] Storm overrides: precipitation=${stormPrecip.toFixed(1)}mm, wind=${stormWind.toFixed(1)}km/h`);

      // Call P2's real LightGBM-backed endpoint (port 8000) with storm overrides
      try {
        const res = await fetch(`${P2_API}/api/supply/trigger-weather-event`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lat: geo.lat,
            lng: geo.lng,
            city: targetCity,
            base_travel_time: 4.0,
            source,
            destination,
            // Storm simulation overrides — P2 uses these instead of live weather
            precipitation_mm: parseFloat(stormPrecip.toFixed(1)),
            wind_speed_kmh: parseFloat(stormWind.toFixed(1)),
          }),
        });
        const data = await res.json();
        console.log(`[SupplyChain] P2 ML response for ${targetCity}:`, data);

        // If P2's model predicted high risk, it already called P3's reroute.
        // If somehow still low risk, update the alert on P3 side.
        if (data.risk_score <= 0.7) {
          await postAction('/supply/trigger-weather-event', {
            edge_a: targetCity,
            edge_b: destination,
            risk_score: data.risk_score,
            gemini_alert: data.gemini_alert || `All clear at ${targetCity}. Risk: ${(data.risk_score * 100).toFixed(0)}%.`,
          });
        }
        return data;
      } catch (err) {
        console.error(`[SupplyChain] P2 offline, falling back to P3 demo:`, err);
        // Fallback: call P3 directly if P2 server is offline
        return postAction('/supply/trigger-weather-event', {
          edge_a: targetCity,
          edge_b: route[route.length - 1] || 'Delhi',
          risk_score: 0.85,
        });
      }
    },
    [postAction, shipment]
  );

  const triggerTrafficEvent = useCallback(
    async () => {
      const route = shipment?.current_route || [];
      let targetCity;
      if (route.length >= 3) {
        const intermediates = route.slice(1, -1);
        targetCity = intermediates[Math.floor(Math.random() * intermediates.length)];
      } else if (route.length > 0) {
        targetCity = route[Math.floor(Math.random() * route.length)];
      } else {
        const allCities = Object.keys(CITY_GEO);
        targetCity = allCities[Math.floor(Math.random() * allCities.length)];
      }

      const geo = CITY_GEO[targetCity];
      if (!geo) {
        console.warn(`[SupplyChain] No coordinates for ${targetCity}, falling back`);
        return postAction('/supply/trigger-weather-event', { edge_a: targetCity, edge_b: 'Delhi', risk_score: 0.85 });
      }

      const source = route[0] || 'Lucknow';
      const destination = route[route.length - 1] || 'Delhi';

      console.log(`[SupplyChain] Simulating traffic at ${targetCity} via P2 ML model...`);

      try {
        const res = await fetch(`${P2_API}/api/supply/trigger-weather-event`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lat: geo.lat,
            lng: geo.lng,
            city: targetCity,
            base_travel_time: 4.0,
            source,
            destination,
            traffic_congestion_ratio: 2.5,
          }),
        });
        const data = await res.json();
        
        if (data.risk_score <= 0.7) {
          await postAction('/supply/trigger-weather-event', {
            edge_a: targetCity,
            edge_b: destination,
            risk_score: data.risk_score,
            gemini_alert: data.gemini_alert || `Traffic check at ${targetCity}. Risk: ${(data.risk_score * 100).toFixed(0)}%.`,
          });
        }
        return data;
      } catch (err) {
        console.error(`[SupplyChain] P2 offline for traffic:`, err);
        return postAction('/supply/trigger-weather-event', {
          edge_a: targetCity,
          edge_b: route[route.length - 1] || 'Delhi',
          risk_score: 0.85,
        });
      }
    },
    [postAction, shipment]
  );

  const startSimulation = useCallback(
    () => postAction('/supply/start-simulation', {}),
    [postAction]
  );

  const stopSimulation = useCallback(
    () => postAction('/supply/stop-simulation', {}),
    [postAction]
  );

  const resetShipment = useCallback(
    () => postAction('/supply/reset-shipment', { source: 'Lucknow', destination: 'Delhi' }),
    [postAction]
  );

  return {
    shipment,
    graphInfo,
    queues,
    activeOrders,
    loading,
    error,
    serverOnline,
    triggerWeatherEvent,
    triggerTrafficEvent,
    startSimulation,
    stopSimulation,
    resetShipment,
  };
}

