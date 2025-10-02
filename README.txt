# Skytation
Senior design project: Parking Enforcement Drone (App, Database & Enforcement subsystem).

## Stack
- Backend: FastAPI + SQLite
- Frontend: React (Vite)
- Streaming: RTSP → FastAPI → React UI
- Database: SQLite for events + permits

## Dev setup
### Backend
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000

### Frontend
cd frontend
npm install
npm run dev

Open: http://localhost:5173
