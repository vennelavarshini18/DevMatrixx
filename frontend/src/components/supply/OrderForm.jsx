import React, { useState } from 'react';
import { Package, MapPin, Tag, Loader2 } from 'lucide-react';

export default function OrderForm({ onOrderPlaced, setError }) {
  const [orderId, setOrderId] = useState('ORD-' + Date.now());
  const [lat, setLat] = useState('27.1');
  const [lng, setLng] = useState('78.0');
  const [items, setItems] = useState('');
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');

  const validate = () => {
    if (!orderId.trim() || !/^[a-zA-Z0-9-]+$/.test(orderId)) {
      return 'Order ID must be non-empty, alphanumeric + hyphens only';
    }
    const latN = parseFloat(lat);
    const lngN = parseFloat(lng);
    if (isNaN(latN) || latN < 8.0 || latN > 37.0) {
      return 'Latitude must be between 8.0 and 37.0 (India)';
    }
    if (isNaN(lngN) || lngN < 68.0 || lngN > 97.0) {
      return 'Longitude must be between 68.0 and 97.0 (India)';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    const err = validate();
    if (err) { setFormError(err); return; }

    setLoading(true);
    const startTime = performance.now();

    try {
      const res = await fetch('http://localhost:8001/order/place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          customer_coords: [parseFloat(lat), parseFloat(lng)],
          items: items.trim() ? items.split(',').map(s => s.trim()) : [],
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || errData.error || 'Order failed');
      }

      const data = await res.json();
      const elapsed = Math.round(performance.now() - startTime);
      onOrderPlaced({ ...data, elapsed_ms: elapsed });

      // Reset form
      setOrderId('ORD-' + Date.now());
      setItems('');
    } catch (err) {
      setFormError(err.message || 'Network error — backend offline?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6 transition-all duration-300">
      {/* Title */}
      <div className="flex items-center gap-3 mb-1">
        <Package className="w-5 h-5 text-blue-300" />
        <h2 className="text-lg font-bold text-white tracking-tight">Place New Order</h2>
      </div>
      <p className="text-[#646464] text-xs font-mono tracking-wide mb-6 ml-8">
        XGBoost selects optimal warehouse in real time
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Order ID */}
        <div>
          <label className="block text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">
            Order ID
          </label>
          <div className="relative">
            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              aria-label="Order ID"
              className="w-full bg-white/[0.04] border border-white/[0.08] text-white text-sm rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:border-blue-300/50 focus:ring-1 focus:ring-blue-300/20 transition-all font-mono placeholder:text-gray-600"
              placeholder="ORD-001"
            />
          </div>
        </div>

        {/* Lat / Lng */}
        <div>
          <label className="block text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">
            Customer Location
          </label>
          <div className="flex gap-3">
            <div className="flex-1">
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="number"
                  step="0.01"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  aria-label="Latitude"
                  className="w-full bg-white/[0.04] border border-white/[0.08] text-white text-sm rounded-lg py-2.5 pl-10 pr-3 focus:outline-none focus:border-blue-300/50 focus:ring-1 focus:ring-blue-300/20 transition-all font-mono"
                  placeholder="Latitude"
                />
              </div>
              <p className="text-[0.6rem] text-gray-600 mt-1 ml-1">Latitude (8–37)</p>
            </div>
            <div className="flex-1">
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="number"
                  step="0.01"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  aria-label="Longitude"
                  className="w-full bg-white/[0.04] border border-white/[0.08] text-white text-sm rounded-lg py-2.5 pl-10 pr-3 focus:outline-none focus:border-blue-300/50 focus:ring-1 focus:ring-blue-300/20 transition-all font-mono"
                  placeholder="Longitude"
                />
              </div>
              <p className="text-[0.6rem] text-gray-600 mt-1 ml-1">Longitude (68–97)</p>
            </div>
          </div>
          <p className="text-[0.6rem] text-gray-500 mt-1.5 ml-1 font-mono">Customer delivery coordinates</p>
        </div>

        {/* Items */}
        <div>
          <label className="block text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">
            Items (optional)
          </label>
          <input
            type="text"
            value={items}
            onChange={(e) => setItems(e.target.value)}
            aria-label="Items"
            className="w-full bg-white/[0.04] border border-white/[0.08] text-white text-sm rounded-lg py-2.5 px-4 focus:outline-none focus:border-blue-300/50 focus:ring-1 focus:ring-blue-300/20 transition-all font-mono placeholder:text-gray-600"
            placeholder="e.g. Electronics, Furniture"
          />
        </div>

        {/* Error */}
        {formError && (
          <p className="text-red-400 text-xs font-mono bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            {formError}
          </p>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          aria-label="Place Order"
          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300 hover:opacity-90 text-indigo-950 font-extrabold text-sm tracking-wider uppercase py-3.5 px-6 rounded-full transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </>
          ) : (
            'Place Order'
          )}
        </button>
      </form>
    </div>
  );
}
