import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8001';

/**
 * Custom hook that polls the P3 Supply Chain FastAPI server for real-time data.
 * Uses HTTP polling (2s interval) — works out of the box with zero extra config.
 * 
 * Returns: shipment state, graph info, warehouse queues, and action functions.
 */
export default function useSupplyChainData() {
  const [shipment, setShipment] = useState(null);
  const [graphInfo, setGraphInfo] = useState(null);
  const [queues, setQueues] = useState({});
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
    (edgeA = 'Agra', edgeB = 'Delhi', riskScore = 0.85) =>
      postAction('/supply/trigger-weather-event', { edge_a: edgeA, edge_b: edgeB, risk_score: riskScore }),
    [postAction]
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
    loading,
    error,
    serverOnline,
    triggerWeatherEvent,
    startSimulation,
    stopSimulation,
    resetShipment,
  };
}
