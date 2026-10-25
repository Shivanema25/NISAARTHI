# Nisaarthi

> Problem Statement 1.1: "The City That Sleeps While You Work"  
> Phase 0 Project Scaffold

## 1. Project Overview

**Nisaarthi** is an intelligent nocturnal mobility and safety companion engineered for night-shift workers, late-night transit riders, and nocturnal urban citizens.

Phase 0 establishes the foundational, minimal project scaffold with:
- A lightweight Python + FastAPI backend exposing an independent health check endpoint.
- A minimal React + Vite frontend that communicates with the backend, displays loading/error/success states, and validates client-server connectivity.
- Isolated configuration, Git ignore rules, and dependency management.

---

## 2. Project Structure

```text
nisaarthi/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore configuration
├── README.md                 # Project documentation
├── backend/
│   ├── .venv/                # Python virtual environment (ignored by Git)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI application entrypoint with CORS
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py     # Independent GET /api/health endpoint
│   ├── requirements.txt      # Backend Python dependencies
│   └── tests/
│       ├── __init__.py
│       └── test_health.py    # Health check automated tests
└── frontend/
    ├── index.html            # HTML entrypoint
    ├── package.json          # Node.js dependencies and scripts
    ├── vite.config.js        # Vite configuration with API reverse proxy
    └── src/
        ├── App.jsx           # Minimal UI displaying health status
        ├── index.css         # Minimal UI styling
        └── main.jsx          # React DOM entrypoint
```

---

## 3. Prerequisites

- **Python**: Version 3.10+ (tested on Python 3.13.5)
- **Node.js**: Version 18+ (tested on Node.js v24.19.0)
- **npm**: Version 9+ (tested on npm 11.17.0)
- **Git**

---

## 4. Backend Installation Instructions

From the project root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

*(On Linux / macOS, use `source .venv/bin/activate` followed by `pip install -r requirements.txt`)*

---

## 5. Backend Startup Command

From the `backend` directory with the virtual environment:

```powershell
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 6. Frontend Installation Instructions

From the project root:

```powershell
cd frontend
npm.cmd install
```

*(Note: On Windows PowerShell if script execution is restricted, invoke `npm.cmd install`)*

---

## 7. Frontend Startup Command

From the `frontend` directory:

```powershell
npm.cmd run dev
```

The frontend will be available at: `http://localhost:5173`

---

## 8. Health Endpoint URL

- **Direct Backend Health URL**: `http://127.0.0.1:8000/api/health`
- **Proxied Frontend Health URL**: `http://localhost:5173/api/health`

### Expected Health Response:
```json
{
  "status": "healthy",
  "service": "Nisaarthi Backend",
  "version": "0.1.0"
}
```

---

## 9. Verifying Frontend/Backend Connectivity

1. Start the backend:
   ```powershell
   cd backend
   .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. In a separate terminal, start the frontend:
   ```powershell
   cd frontend
   npm.cmd run dev
   ```
3. Open `http://localhost:5173` in a web browser.
4. Verify that the UI displays **Nisaarthi**, followed by a green **"Backend Healthy"** badge and the formatted JSON payload returned from the backend.
5. To test failure handling: stop the backend process and click **"Re-check Health Endpoint"** on the frontend. The UI will transition to the red **"Backend Unavailable"** badge and display the connection error.
6. To run backend automated unit tests:
   ```powershell
   cd backend
   .venv\Scripts\pytest
   ```
