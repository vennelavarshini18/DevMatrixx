import React, { useState, useEffect } from 'react';

export default function CustomerForm({ onOrderPlaced }) {
  const [inventory, setInventory] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/inventory')
      .then(res => res.json())
      .then(data => {
        setInventory(data.inventory);
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  const placeOrder = async (item) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.error) {
          alert(data.error);
        } else {
          onOrderPlaced(); // Navigate to the warehouse view
        }
      } else {
        alert("Server error occurred");
      }
    } catch(err) {
      console.error(err);
      alert("Network error occurred");
    }
  };

  const products = [
    { id: 'face_cream', name: 'Face Cream', image: '✨', section: 'Skincare', color: 'bg-pink-500', hover: 'hover:bg-pink-400' },
    { id: 'coffee', name: 'Artisan Coffee', image: '☕', section: 'Grocery', color: 'bg-yellow-600', hover: 'hover:bg-yellow-500' },
    { id: 'sneakers', name: 'Sneakers', image: '👟', section: 'Footwear', color: 'bg-orange-500', hover: 'hover:bg-orange-400' },
    { id: 'tshirt', name: 'Cotton T-Shirt', image: '👕', section: 'Clothes', color: 'bg-emerald-500', hover: 'hover:bg-emerald-400' },
    { id: 'vitamins', name: 'Multivitamins', image: '💊', section: 'Pharmacy', color: 'bg-teal-500', hover: 'hover:bg-teal-400' },
    { id: 'laptop', name: 'Pro Laptop', image: '💻', section: 'Electronics', color: 'bg-blue-600', hover: 'hover:bg-blue-500' },
    { id: 'notebook', name: 'Leather Notebook', image: '📓', section: 'Stationery', color: 'bg-indigo-500', hover: 'hover:bg-indigo-400' },
    { id: 'smartwatch', name: 'Smartwatch', image: '⌚', section: 'Accessories', color: 'bg-slate-700', hover: 'hover:bg-slate-600' }
  ];

  if (loading) return <div className="w-screen h-screen flex justify-center items-center bg-gray-950 font-mono text-cyan-400 text-xl tracking-widest uppercase">Initializing Storefront...</div>;

  return (
    <div className="w-screen min-h-screen bg-gray-950 text-white overflow-y-auto overflow-x-hidden font-sans">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <header className="mb-20 text-center">
          <h1 className="text-6xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent">Nexus Storefront</h1>
          <p className="text-gray-400 mt-6 text-xl font-light">Experience autonomous next-generation fulfillment</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {products.map((prod) => {
            const stock = inventory[prod.id] || 0;
            const inStock = stock > 0;
            return (
              <div key={prod.id} className="bg-gray-900 border border-gray-800 rounded-3xl p-6 shadow-2xl hover:shadow-cyan-900/40 transition-all duration-300 transform hover:-translate-y-2 group">
                <div className="text-6xl mb-6 text-center group-hover:scale-110 transition-transform duration-300 ease-out">{prod.image}</div>
                <h3 className="text-2xl font-bold text-center mb-1">{prod.name}</h3>
                <p className="text-gray-400 text-center text-xs mb-6 uppercase tracking-widest font-bold">{prod.section}</p>
                
                <div className="flex justify-between items-center mb-6 px-4 py-3 bg-gray-800/50 rounded-xl">
                    <span className="text-gray-400 font-medium tracking-wide text-sm">Stock Level</span>
                    <span className={`font-mono text-xl font-bold ${inStock ? 'text-green-400' : 'text-red-500'}`}>
                        {inStock ? stock : 'OUT'}
                    </span>
                </div>

                <button 
                  onClick={() => placeOrder(prod.id)}
                  disabled={!inStock}
                  className={`w-full py-4 rounded-xl font-bold text-lg shadow-lg flex items-center justify-center gap-2 transition-all ${inStock ? `${prod.color} ${prod.hover} text-white cursor-pointer group-hover:shadow-[0_0_15px_rgba(56,189,248,0.4)]` : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'}`}
                >
                  {inStock ? (
                      <>
                        Buy Now
                        <svg className="w-6 h-6 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                      </>
                  ) : 'Out of Stock'}
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  );
}
