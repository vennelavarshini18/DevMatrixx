# WareFlow: Autonomous Warehouse AI

## The Problem
Modern e-commerce warehouses are massive, chaotic labyrinths. Relying on human workers to manually walk miles every day to search for items across thousands of shelves is physically exhausting, highly inefficient, and a massive bottleneck. The industry loses millions of dollars daily due to slow picking times, gridlocks in warehouse aisles, and rigid, hard-coded routing systems that fail the moment demand shifts.

## The Solution (WareFlow)
WareFlow is an end-to-end, completely autonomous warehouse fulfillment matrix built for high-performance dynamic routing. By bridging advanced Reinforcement Learning intelligence with a real-time **React Three Fiber** 3D digital twin, we’ve created a flexible AI that actively learns how to navigate complex environments instantly without relying on hardcoded paths.

## How to Run (Local Deployment)

To start the WareFlow simulation, you will need to boot both the FastAPI server and the React Web Application simultaneously.

### 1. Boot the Backend (API + AI Engine)
```bash
cd backend
python3 -m uvicorn main:app --reload
```
*Ensure you have your virtual environment active with `fastapi`, `uvicorn`, `torch`, and `stable-baselines3` installed.*

### 2. Boot the Frontend (Web + 3D Canvas)
```bash
cd frontend
npm install
npm run dev
```

Navigate to the provided localhost URL (typically `http://localhost:5173` or `http://localhost:3000`) in your browser to access the DevMatrixx Control Panel.
