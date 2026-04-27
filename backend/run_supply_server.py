"""
WareFlow Supply Chain Server Launcher

Starts the supply chain API on port 8001.
The existing RL warehouse server continues to run on port 8000 — no conflicts.

Usage:
    cd backend
    python run_supply_server.py

    # Or directly with uvicorn:
    cd backend
    uvicorn supply_chain.app:app --port 8001 --reload
"""

import uvicorn

if __name__ == "__main__":
    print("\n--- Starting WareFlow Supply Chain Server ---")
    print("   Port: 8001")
    print("   Docs: http://localhost:8001/docs")
    print("   Existing RL server: http://localhost:8000 (unaffected)\n")

    uvicorn.run(
        "supply_chain.app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
