import React from 'react';

export default function HUD({ frameData, speedMultiplier, onSpeedChange }) {
  if (!frameData) return null;

  const { stage, step, episode, metrics } = frameData;
  const reward = metrics?.reward_this_step || 0;
  
  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {/* Top Right Panel */}
      <div className="absolute top-4 right-4 bg-gray-900/80 backdrop-blur-md text-white/90 p-4 rounded-xl border border-white/10 w-64 shadow-2xl pointer-events-auto">
        <h2 className="text-lg font-bold mb-3 border-b border-white/10 pb-2">RL Stats</h2>
        <div className="space-y-1 text-sm font-mono tracking-tight">
          <div className="flex justify-between"><span>Stage:</span><span>{stage}</span></div>
          <div className="flex justify-between"><span>Step:</span><span>{step}</span></div>
          <div className="flex justify-between"><span>Episode:</span><span>{episode}</span></div>
          <div className="flex justify-between">
            <span>Reward (step):</span>
            <span className={reward > 0 ? 'text-green-400' : reward < 0 ? 'text-red-400' : ''}>
              {reward > 0 ? `+${reward.toFixed(2)}` : reward.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between"><span>Total Reward:</span><span>{metrics?.total_reward?.toFixed(2) || 0}</span></div>
          <div className="flex justify-between"><span>Dist to Goal:</span><span>{metrics?.distance_to_goal?.toFixed(2) || 0}</span></div>
        </div>
      </div>

      {/* Bottom Left Panel (formerly Center) */}
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
        <span className="font-mono text-sm w-8 text-right">{speedMultiplier}×</span>
      </div>
    </div>
  );
}
