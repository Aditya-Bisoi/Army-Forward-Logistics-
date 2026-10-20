# Predictive Forward Logistics Digital Twin
> **SIH 2026 · Problem Statement PS26251**  
> *AI-Driven Decision Support for the Last Mile of Operational Readiness*

A comprehensive Geospatial Digital Twin and Predictive Logistics platform built for defense forward-operating environments (Ladakh / Leh operational sectors). It combines machine learning demand forecasting, dynamic multi-criteria route optimization, and proactive "What-If" crisis simulation with human-in-the-loop command authority.

---

## 🚀 Key Features

1. **Operational Control Tower (Geospatial Digital Twin)**
   - Interactive high-altitude terrain map (Leaflet) tracking Depots, Distribution Hubs, and Forward Operating Locations.
   - Live KPI monitoring: network inventory availability, critical nodes, active convoys, and compromised corridors.
   - **Twin Inspector**: Transparent, explainable risk contributor breakdown (*Inventory cover, Route reliability, Weather exposure, Demand trend*).

2. **Machine Learning Demand Forecasting**
   - Trained **Scikit-Learn Random Forest Regressor** evaluating multi-echelon consumption history (180 days).
   - Rolling window averages (7, 14, 28-day lags), troop headcount dynamics, and day-of-week seasonality.
   - Live model evaluation metrics (**MAE, RMSE, MAPE**) and multi-commodity tracking (*Fuel, Rations, Medical, Spares*).

3. **Multi-Criteria Graph Route Optimizer & Fleet Allocation**
   - Instant calculation and ranking of **Top-3 Corridors**: Primary (Gold), Alternate (Green), and Fallback (Grey).
   - Dynamic tactical weighting sliders for **Travel Time**, **Corridor Risk**, and **Capacity**.
   - Automated vehicle allocation pairing Fuel Tankers, Heavy Cargo Trucks, and Light Utility 4x4s against cargo demand.

4. **"What-If" Crisis Simulation & Human-in-the-Loop Command**
   - Real-time tactical stress-testing:
     - *Sudden Demand Surge (+42% fuel consumption)*
     - *Primary Route Blockage (Simulated mountain pass closure)*
     - *Severe Weather (+6 hours delay across exposed passes)*
     - *Vehicle Breakdown (Fleet asset offline)*
   - Quantified **Before vs. After** metrics: stockout probability reduction and delivery ETA.
   - Strict military human-in-the-loop: Commander can **Approve**, **Modify Quantity**, or **Reject**.

5. **Admin Console & MLOps Lifecycle**
   - Dynamic risk factor weight calibration.
   - Full CRUD entity management for nodes, routes, and vehicle fleets.
   - On-demand ML retraining, custom CSV data ingestion, and zero-downtime model hot-swapping/rollback.
   - Cryptographically tracked, tamper-evident audit trail for all supply decisions.

---

## 🛠️ Architecture & Tech Stack

- **Frontend**: React 19, CRACO, TailwindCSS, Lucide Icons, Leaflet / React-Leaflet, Recharts, Framer Motion.
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic, Scikit-learn, Pandas, NumPy, Motor / MongoMock fallback.
- **Authentication**: JWT-based session management with secure cookies and bcrypt password hashing.

---

## 🏁 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
*Backend runs at `http://localhost:8000` (Health Check: `http://localhost:8000/api/health`)*

### 3. Frontend Setup
```bash
cd frontend
npm install
npm start
```
*Frontend runs at `http://localhost:3000`*

---

## 🔐 Default Access Credentials

- **Admin Email**: `admin@forwardlogistics.demo`
- **Password**: `ControlTower2026!`

---

## 📜 License
Developed for Smart India Hackathon (SIH 2026). All rights reserved.
