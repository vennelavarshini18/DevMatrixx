/**
 * Firebase client initialization for WareFlow frontend.
 * Provides real-time listeners for warehouse queues and active shipment state.
 */

import { initializeApp, getApps } from 'firebase/app';
import { getDatabase, ref, onValue } from 'firebase/database';

const firebaseConfig = {
  databaseURL: 'https://wareflow-f8b9f-default-rtdb.firebaseio.com/',
};

// Guard against duplicate initialization
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const db = getDatabase(app);

/**
 * Subscribe to real-time warehouse queue updates.
 * @param {Function} callback - called with { lucknow: { pending, coords }, delhi: { pending, coords } }
 * @returns {Function} unsubscribe function
 */
export function subscribeToWarehouseQueues(callback) {
  const warehousesRef = ref(db, 'warehouses');
  const unsub = onValue(warehousesRef, (snapshot) => {
    const data = snapshot.val();
    if (data) callback(data);
  }, (error) => {
    console.error('Firebase warehouses listener error:', error);
  });
  return unsub;
}

/**
 * Subscribe to real-time active shipment updates.
 * @param {Function} callback - called with { order_id, status, current_route, risk_score, eta_hours, gemini_alert }
 * @returns {Function} unsubscribe function
 */
export function subscribeToActiveShipment(callback) {
  const shipmentRef = ref(db, 'active_shipment');
  const unsub = onValue(shipmentRef, (snapshot) => {
    const data = snapshot.val();
    if (data) callback(data);
  }, (error) => {
    console.error('Firebase active_shipment listener error:', error);
  });
  return unsub;
}

export { db };
