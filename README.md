# WareFlow: Resilient Logistics and Dynamic Supply Chain


## The Opportunity
Traditional logistics operations are highly reactive. We provide a comprehensive **Admin Command Center** that transforms reactive logistics into a proactive, autonomous ecosystem.

## The Solution & USP
**The Solution:** WareFlow uses Reinforcement Learning for internal warehouse fulfillment and intelligent shortest-path routing between cities.  
**Unique Selling Proposition (USP):** An end-to-end "intelligent" journey where an ML model predicts route disruptions, including both extreme weather and live traffic, to autonomously reroute shipments in real-time.

---

## List of Features

- **Admin Dashboard**: A centralized web interface for total oversight of orders, inventory, and global fleet status.
- **Autonomous RL Fulfillment**: A trained model navigates robots through warehouse grids to pick items with zero human intervention.
- **3D Digital Twin**: Live visualization of the warehouse floor directly within the admin view.
- **Predictive Risk Engine**: Monitors live weather and traffic data to assign risk scores to every transit route.
- **Dynamic Rerouting**: Automatically recalculates and updates paths in the system when high risks are detected.
- **Gemini AI Alerts**: Generates natural language reasoning to explain disruption risks to the admin.

---

## Core Algorithms

WareFlow leverages a suite of powerful algorithms to drive its autonomous operations:
- **XGBoost**: Employed to efficiently and intelligently select the optimal warehouse based on real-time factors like inventory levels, distance, and fulfillment load.
- **Dijkstra’s Algorithm**: Implemented for calculating the global shortest path across the 22-city highway graph network.
- **Reinforcement Learning (PPO)**: Powers the autonomous agent's micro-navigation, pathfinding, and obstacle avoidance within the warehouse grid.
- **LightGBM**: A Gradient Boosting model utilized for high-accuracy prediction of transit risks caused by extreme weather and traffic events.

---

## Technologies & Google Integrations

### Tech Stack
- **Frontend (Admin Command Center)**: React.js, Three.js, React Three Fiber, Tailwind CSS.
- **Backend Ecosystem**: Dual-server architecture using FastAPI (Python) for high-performance async processing and WebSockets for live streaming.
- **Cloud & Database**: Firebase Realtime Database for global state synchronization and Google Cloud Platform for scalable deployment.

---

## 🛠️ Local Setup & Execution

### Prerequisites
- Python 3.10+
- Node.js 20.19+
- A `serviceAccountKey.json` placed in the `wareflow_p1/` directory.
- A `backend/.env` file containing `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY`.

### 1. Boot the Unified Backend (FastAPI + WebSockets)
```bash
cd backend
pip install -r requirements.txt
python run_backend.py
```

### 2. Boot the Frontend Command Center (React)
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173` to access the Admin Command Center.

---
### Project Links
- **Demo Video:** [Watch here](https://drive.google.com/file/d/1_e_FabP5ld-Hk2iZ5TubcSKPOj4peNUV/view)
