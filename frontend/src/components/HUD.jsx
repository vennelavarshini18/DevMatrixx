import React from 'react';

export default function HUD({ frameData, speedMultiplier, onSpeedChange, onBack }) {
  if (!frameData) return null;

  const { stage, step, episode, metrics, agent, goal, robot_state } = frameData;
  const reward = metrics?.reward_this_step || 0;
  
  // Prioritize global orchestrator status over internal agent status
  const status = robot_state?.status === 'delivered' ? 'delivered' : (agent?.status || 'moving');

  // Status display config
  const statusConfig = {
    moving: { label: 'Navigating', color: 'text-blue-400', icon: '\u2192' },
    blocked: { label: 'Wall Hit', color: 'text-yellow-400', icon: '\u2298' },
    collided: { label: 'COLLISION!', color: 'text-red-400 animate-pulse', icon: '\u2715' },
    reached_goal: { label: 'FETCHING...', color: 'text-green-400 animate-pulse', icon: '\u2713' },
    delivered: { label: 'DELIVERED!', color: 'text-emerald-400 font-bold', icon: '\u2713\u2713' },
  };
  const sc = statusConfig[status] || statusConfig.moving;

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      
      {/* ── TOP SECTION INVENTORY TRACKER ── */}
      <div className="absolute top-0 left-0 right-0 bg-gray-900/90 backdrop-blur-md border-b border-white/10 flex justify-center items-center py-3 px-6 shadow-2xl pointer-events-auto">
        {onBack && (
            <button onClick={onBack} className="absolute left-6 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-bold transition-colors shadow-lg z-[110]">
               &larr; Back to Store
            </button>
        )}
        <div className="flex gap-6 max-w-7xl overflow-x-auto w-full justify-center">
            {frameData.inventory && Object.entries(frameData.inventory).map(([key, count]) => {
                const labelMap = {face_cream: 'Skincare', coffee: 'Grocery', sneakers: 'Footwear', tshirt: 'Clothes', vitamins: 'Pharmacy', laptop: 'Electronics', notebook: 'Stationery', smartwatch: 'Accessories'};
                const label = labelMap[key] || key;
                return (
                    <div key={key} className="flex flex-col items-center bg-gray-800/50 px-4 py-2 rounded-lg min-w-[120px] shadow-inner">
                        <span className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1">{label}</span>
                        <span className={`text-xl font-mono font-bold ${count > 0 ? 'text-green-400' : 'text-red-500 animate-pulse'}`}>
                            {count > 0 ? count : 'OUT'}
                        </span>
                    </div>
                )
            })}
        </div>
      </div>

      {/* ── MASSIVE DELIVERY SUCCESS TOAST ── */}
      {status === 'delivered' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm z-[100] animate-in fade-in zoom-in duration-700">
            <div className="bg-emerald-500 text-white px-12 py-8 rounded-[3rem] shadow-[0_0_100px_rgba(16,185,129,0.5)] border-4 border-emerald-400 transform transition-all flex flex-col items-center">
                <span className="text-8xl mb-4">📦</span>
                <h1 className="text-6xl font-extrabold tracking-tight mb-2 uppercase">Delivery Successful</h1>
                <p className="text-emerald-100 text-xl font-mono font-medium opacity-90">Inventory automatically decremented</p>
            </div>
        </div>
      )}

      {/* Top Right Panel */}
      <div className="absolute top-24 right-4 bg-gray-900/80 backdrop-blur-md text-white/90 p-4 rounded-xl border border-white/10 w-72 shadow-2xl pointer-events-auto">
        <h2 className="text-lg font-bold mb-3 border-b border-white/10 pb-2">RL Stats</h2>
        <div className="space-y-1 text-sm font-mono tracking-tight">
          <div className="flex justify-between"><span>Stage:</span><span className="text-cyan-400">{stage}</span></div>
          <div className="flex justify-between"><span>Step:</span><span>{step}</span></div>
          <div className="flex justify-between"><span>Episode:</span><span>{episode}</span></div>
          <div className="flex justify-between">
            <span>Status:</span>
            <span className={sc.color}>{sc.icon} {sc.label}</span>
          </div>
          <div className="border-t border-white/10 my-2" />
          <div className="flex justify-between">
            <span>Reward (step):</span>
            <span className={reward > 0 ? 'text-green-400' : reward < 0 ? 'text-red-400' : ''}>
              {reward > 0 ? `+${reward.toFixed(2)}` : reward.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between"><span>Total Reward:</span><span>{metrics?.total_reward?.toFixed(2) || 0}</span></div>
          <div className="flex justify-between"><span>Dist to Goal:</span><span>{metrics?.distance_to_goal?.toFixed(2) || 0}</span></div>
          <div className="border-t border-white/10 my-2" />
          <div className="flex justify-between"><span>Agent Pos:</span><span className="text-blue-400">({agent?.x}, {agent?.y})</span></div>
          <div className="flex justify-between"><span>Goal Dest:</span><span className="text-green-400">({goal?.x}, {goal?.y})</span></div>
        </div>
      </div>

      {/* Bottom Left Panel */}
      <div className="absolute bottom-6 left-6 bg-gray-900/80 backdrop-blur-md text-white p-4 rounded-xl border border-white/10 flex items-center gap-4 shadow-2xl pointer-events-auto">
        <label htmlFor="speed" className="font-bold text-sm">Speed</label>
        <input
          id="speed"
          type="range"
          min="1"
          max="10"
          step="1"
          value={speedMultiplier}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
          className="w-48 accent-blue-500"
        />
        <span className="font-mono text-sm w-8 text-right">{speedMultiplier}x</span>
      </div>
    </div>
  );
}