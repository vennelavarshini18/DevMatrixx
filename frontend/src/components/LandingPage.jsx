import React from 'react';
import MiniCityScene from './MiniCityScene';

const LandingPage = ({ onGetStarted, onSupplyChain }) => {
  return (
    <div className="min-h-screen w-full bg-[#050505] flex flex-col font-sans text-gray-100 overflow-hidden relative">
      
      {/* Decorative ambient gradients (Soft Pastel) */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-300/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-300/10 blur-[120px] pointer-events-none" />

      {/* --- TOP NAVBAR --- */}
      <nav className="w-full max-w-[100rem] mx-auto px-8 md:px-12 py-8 flex items-center justify-between z-10 relative">
        <div className="flex items-center gap-2 font-black text-2xl tracking-tighter cursor-default select-none text-white">
          <div className="w-3.5 h-3.5 bg-gradient-to-tr from-blue-300 to-purple-300 rounded-full shadow-[0_0_8px_rgba(147,197,253,0.5)]" />
          WAREFLOW
        </div>
        
        <div className="hidden md:flex gap-10 font-bold text-sm tracking-wide text-gray-400">
          {onSupplyChain && <button onClick={onSupplyChain} className="hover:text-blue-300 transition-colors">SUPPLY CHAIN</button>}
          <button className="hover:text-blue-300 transition-colors">DASHBOARD</button>
          <button className="hover:text-blue-300 transition-colors">FLEET</button>
          <button className="hover:text-blue-300 transition-colors">ANALYTICS</button>
        </div>
      </nav>

      {/* --- MAIN HERO CONTENT --- */}
      <main className="flex-1 w-full max-w-[100rem] mx-auto px-8 md:px-12 flex flex-col lg:flex-row items-center justify-between pb-12 z-10 relative">
        
        {/* Left Side: Text and CTA */}
        <div className="w-full lg:w-2/5 pt-10 lg:pt-0 z-30">
          <h1 className="text-[4.5rem] md:text-[6rem] font-medium leading-[1.05] tracking-[-.04em] text-white mb-6">
            Smart <br />
            <span className="font-serif font-light italic text-gray-400 tracking-normal">Logistics.</span>
          </h1>
          
          <h2 className="text-sm font-semibold text-gray-300 mb-6 tracking-[0.15em] uppercase opacity-80">
            Next-Gen Robotics Delivery
          </h2>
          
          <p className="text-[#646464] text-base md:text-lg leading-relaxed max-w-md mb-10 font-mono tracking-[0.05em]">
            Automate your supply chain effortlessly. Browse our premium catalogue containing cosmetics, electronics, and groceries, and watch our neural-network powered fleet dispatch your items in real-time.
          </p>
          
          <button 
             onClick={onGetStarted}
             className="group flex items-center gap-3 bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300 hover:opacity-90 text-indigo-950 font-extrabold text-sm tracking-wider uppercase py-4 px-8 rounded-full transition-all transform hover:-translate-y-0.5"
          >
            Shop Now
            <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Right Side: Massive Interactive 3D Mini Warehouse */}
        <div className="w-full lg:w-3/5 flex justify-center lg:justify-end mt-16 lg:mt-0 relative select-none z-20">
          <div className="relative w-full max-w-[1000px] h-[50vh] lg:h-[80vh] flex items-center justify-center">
             {/* Deep background ambient glow to frame the 3D element */}
             <div className="absolute w-[90%] h-[90%] bg-gradient-to-tr from-blue-300/10 to-purple-300/10 blur-[130px] rounded-full pointer-events-none" />
             
             {/* 3D Canvas */}
             <MiniCityScene />
          </div>
        </div>

      </main>

    </div>
  );
};

export default LandingPage;
