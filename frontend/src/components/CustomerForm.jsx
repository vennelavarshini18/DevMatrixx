import React, { useState, useEffect } from 'react';

const CATEGORIES = [
  { 
    id: 'grocery', 
    name: 'Grocery', 
    image: 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=600', 
    items: ['Milk', 'Eggs', 'Chocolates', 'Detergent', 'Flour', 'Bread'],
    neon: 'hover:shadow-[0_0_15px_rgba(0,255,255,0.4)] hover:border-cyan-400',
    textNeon: 'group-hover:text-cyan-400',
    btnNeon: 'hover:border-cyan-400 hover:bg-cyan-900/30 hover:text-cyan-300',
    bgNeon: 'bg-cyan-500'
  },
  { 
    id: 'electronics', 
    name: 'Electronics', 
    image: 'https://images.unsplash.com/photo-1498049794561-7780e7231661?auto=format&fit=crop&q=80&w=600', 
    items: ['Laptop', 'Smartwatch', 'Headphones', 'Cables'],
    neon: 'hover:shadow-[0_0_15px_rgba(138,43,226,0.4)] hover:border-purple-500',
    textNeon: 'group-hover:text-purple-400',
    btnNeon: 'hover:border-purple-500 hover:bg-purple-900/30 hover:text-purple-300',
    bgNeon: 'bg-purple-500'
  },
  { 
    id: 'pharmacy', 
    name: 'Pharmacy', 
    image: 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&q=80&w=600', 
    items: ['Vitamins', 'Painkillers', 'First Aid', 'Masks'],
    neon: 'hover:shadow-[0_0_15px_rgba(57,255,20,0.4)] hover:border-green-400',
    textNeon: 'group-hover:text-green-400',
    btnNeon: 'hover:border-green-400 hover:bg-green-900/30 hover:text-green-300',
    bgNeon: 'bg-green-500'
  },
  { 
    id: 'skincare', 
    name: 'Skincare', 
    image: 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&fit=crop&q=80&w=600', 
    items: ['Face Cream', 'Sunscreen', 'Serum', 'Lotion'],
    neon: 'hover:shadow-[0_0_15px_rgba(255,0,255,0.4)] hover:border-fuchsia-500',
    textNeon: 'group-hover:text-fuchsia-400',
    btnNeon: 'hover:border-fuchsia-500 hover:bg-fuchsia-900/30 hover:text-fuchsia-300',
    bgNeon: 'bg-fuchsia-500'
  },
  { 
    id: 'footwear', 
    name: 'Footwear', 
    image: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&q=80&w=600', 
    items: ['Sneakers', 'Boots', 'Sandals', 'Socks'],
    neon: 'hover:shadow-[0_0_15px_rgba(255,69,0,0.4)] hover:border-orange-500',
    textNeon: 'group-hover:text-orange-400',
    btnNeon: 'hover:border-orange-500 hover:bg-orange-900/30 hover:text-orange-300',
    bgNeon: 'bg-orange-500'
  },
  { 
    id: 'clothes', 
    name: 'Clothes', 
    image: 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&q=80&w=600', 
    items: ['T-Shirt', 'Jeans', 'Jacket', 'Sweater'],
    neon: 'hover:shadow-[0_0_15px_rgba(255,255,0,0.4)] hover:border-yellow-400',
    textNeon: 'group-hover:text-yellow-400',
    btnNeon: 'hover:border-yellow-400 hover:bg-yellow-900/30 hover:text-yellow-300',
    bgNeon: 'bg-yellow-500'
  },
  { 
    id: 'stationery', 
    name: 'Stationery', 
    image: 'https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?auto=format&fit=crop&q=80&w=600', 
    items: ['Notebook', 'Pens', 'Markers', 'Stapler'],
    neon: 'hover:shadow-[0_0_15px_rgba(65,105,225,0.4)] hover:border-blue-500',
    textNeon: 'group-hover:text-blue-400',
    btnNeon: 'hover:border-blue-500 hover:bg-blue-900/30 hover:text-blue-300',
    bgNeon: 'bg-blue-500'
  },
  { 
    id: 'accessories', 
    name: 'Accessories', 
    image: 'https://images.unsplash.com/photo-1523206489230-c012c64b2b48?auto=format&fit=crop&q=80&w=600', 
    items: ['Watch', 'Sunglasses', 'Belt', 'Wallet'],
    neon: 'hover:shadow-[0_0_15px_rgba(200,200,200,0.4)] hover:border-gray-300',
    textNeon: 'group-hover:text-gray-300',
    btnNeon: 'hover:border-gray-300 hover:bg-gray-800/50 hover:text-gray-200',
    bgNeon: 'bg-gray-400'
  }
];

export default function NexusStorefront({ onOrderPlaced }) {
  const [inventory, setInventory] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/inventory')
      .then(res => res.json())
      .then(data => {
        setInventory(data.inventory);
        setLoading(false);
      })
      .catch(err => {
        console.error("Backend offline?");
        setLoading(false);
      });
  }, []);

  const placeOrder = async (categoryId, itemName) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: categoryId, item: itemName })
      });
      if (res.ok) {
        if(onOrderPlaced) onOrderPlaced();
      } else {
        const errorData = await res.json();
        alert(`Failed: ${errorData.error}`);
      }
    } catch (err) { alert("Network Error"); }
  };

  if (loading) return (
    <div className="w-screen h-screen flex justify-center items-center bg-[#030303] font-mono text-cyan-400 text-sm tracking-[0.3em] uppercase text-center">
      <div className="animate-pulse">INITIALIZING SECURE LINK...</div>
    </div>
  );

  return (
    <div className="w-screen min-h-screen bg-[#050505] text-gray-300 overflow-y-auto overflow-x-hidden font-sans p-8 selection:bg-cyan-900 selection:text-cyan-100">
      
      {/* Background vignette wrapper to simulate dark warehouse alley */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-transparent via-[#000000d0] to-[#000000] z-0"></div>

      <div className="max-w-7xl mx-auto relative z-10">
        <header className="mb-16 mt-8 flex flex-col items-center border-b border-gray-800/50 pb-8">
          <div className="h-[1px] w-48 bg-gradient-to-r from-transparent via-cyan-500 to-transparent mb-6 opacity-30"></div>
          <h1 className="text-4xl font-light tracking-[0.2em] text-gray-300 mb-2 uppercase" style={{textShadow: "0 0 20px rgba(0, 255, 255, 0.2)"}}>
            STORE <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-300 via-indigo-300 to-purple-300">FRONT</span>
          </h1>
          <p className="text-[#646464] uppercase tracking-[0.3em] text-[0.65rem] font-mono">
            Autonomous Fulfillment Routing
          </p>
          <div className="h-[1px] w-48 bg-gradient-to-r from-transparent via-purple-500 to-transparent mt-6 opacity-30"></div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {CATEGORIES.map((cat) => {
            const stock = (inventory || {})[cat.id] || 0;
            const inStock = stock > 0;

            return (
              <div 
                key={cat.id} 
                className={`group relative overflow-hidden bg-[#0a0a0a] border ${inStock ? 'border-[#1a1a1a]' : 'border-red-900/30'} 
                  rounded-xl transition-all duration-500 ${inStock ? cat.neon : ''}`}
              >
                {/* Background Image with Neon Color Overlay */}
                <div 
                  className="absolute inset-0 z-0 opacity-40 group-hover:opacity-60 transition-opacity duration-700 blur-[2px] group-hover:blur-0"
                  style={{ backgroundImage: `url(${cat.image})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
                ></div>
                {/* 50% blend of exact neon color */}
                <div className={`absolute inset-0 z-0 opacity-50 mix-blend-color ${inStock ? cat.bgNeon : 'bg-gray-800'}`}></div>
                <div className="absolute inset-0 z-[1] bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a]/70 to-[#0a0a0a]/20"></div>

                <div className="relative z-10 p-6 h-full flex flex-col">
                  
                  {/* Header Row */}
                  <div className="flex justify-between items-end mb-8 border-b border-gray-800/50 pb-4">
                    <h3 className={`text-xl font-light tracking-[0.1em] uppercase text-gray-200 transition-colors duration-300 ${inStock ? cat.textNeon : ''}`}>
                      {cat.name}
                    </h3>
                    
                    {/* Status Badge */}
                    <div className="flex flex-col items-end">
                      {inStock ? (
                        <>
                          <span className="text-[0.55rem] tracking-[0.2em] font-mono text-gray-300 uppercase opacity-90">Reserves</span>
                          <span className="text-sm font-bold text-white">{stock.toString().padStart(3, '0')}</span>
                        </>
                      ) : (
                        <span className="text-[0.6rem] tracking-[0.15em] font-mono text-red-500/80 border border-red-500/30 px-2 py-0.5 rounded uppercase">
                          Depleted
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Items list */}
                  <div className="flex flex-col gap-2 flex-grow">
                    {cat.items.map(item => (
                      <button
                        key={item}
                        disabled={!inStock}
                        onClick={() => placeOrder(cat.id, item)}
                        className={`text-xs text-left px-4 py-2.5 rounded border transition-all tracking-[0.05em] flex justify-between items-center group/btn
                          ${inStock 
                            ? `border-gray-800/80 bg-black/40 text-gray-400 cursor-pointer ${cat.btnNeon}` 
                            : 'border-transparent text-gray-700 bg-black/20 cursor-not-allowed'}`}
                      >
                        <span className="font-light">{item}</span>
                        {inStock && (
                          <span className="opacity-0 group-hover/btn:opacity-100 transition-opacity duration-300 text-[0.6rem] font-mono tracking-widest">
                            [ DISPATCH ]
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
