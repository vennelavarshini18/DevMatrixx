import React, { useState } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';

const METRICS = [
  { label: 'Accuracy', value: '98.05%', bar: true, barWidth: 98 },
  { label: 'Train Dataset', value: '10,000 rows', bar: false },
  { label: 'Features', value: '4 input cols', bar: false },
  { label: 'Inference', value: '<12ms per order', bar: false },
  { label: 'Top Feature', value: 'distance_to_wh2', bar: false },
  { label: 'Selection Logic', value: 'distance + queue penalty weighting', bar: false },
];

export default function WarehouseIntelligenceCard() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl rounded-2xl p-6 transition-all duration-300">
      {/* Title */}
      <div className="flex items-center gap-3 mb-1">
        <Brain className="w-5 h-5 text-blue-300" />
        <h2 className="text-lg font-bold text-white tracking-tight">Warehouse Intelligence</h2>
      </div>
      <p className="text-[#646464] text-xs font-mono tracking-wide mb-5 ml-8">
        XGBoost selection model stats
      </p>

      {/* Model name */}
      <div className="flex items-center gap-2 mb-4 p-2.5 bg-white/[0.04] rounded-xl border border-white/[0.06]">
        <Brain className="w-4 h-4 text-blue-300" />
        <span className="text-sm text-white font-semibold">Model: XGBoost Classifier</span>
      </div>

      {/* Metrics */}
      <div className="space-y-0">
        {METRICS.map((m, i) => (
          <div
            key={i}
            className="flex items-center justify-between py-2.5 border-l-2 border-blue-300/30 pl-4 hover:bg-white/[0.02] transition-colors"
          >
            <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">{m.label}</span>
            <div className="flex items-center gap-2">
              {m.bar && (
                <div className="w-20 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-300 to-purple-300 rounded-full"
                    style={{ width: `${m.barWidth}%` }}
                  />
                </div>
              )}
              <span className="text-sm text-white font-mono">{m.value}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Collapsible How It Works */}
      <div className="mt-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-xs text-gray-400 hover:text-blue-300 transition-colors font-semibold uppercase tracking-wider"
          aria-label="Toggle how it works"
        >
          How it works
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
        <div
          className="overflow-hidden transition-all duration-300 ease-in-out"
          style={{ maxHeight: expanded ? '200px' : '0px', opacity: expanded ? 1 : 0 }}
        >
          <p className="text-xs text-gray-500 font-mono leading-relaxed mt-3 p-3 bg-white/[0.02] rounded-lg border border-white/[0.04]">
            For each new order, WareFlow fetches real driving distances via Google Maps API,
            combines them with live Firebase queue depths, and runs them through a trained
            XGBoost classifier to select the optimal warehouse in under 12ms.
          </p>
        </div>
      </div>
    </div>
  );
}
