# Skytation
Senior design project: Parking Enforcement Drone (App, Database & Enforcement subsystem).

## Stack
- Backend: FastAPI + SQLite
- Frontend: React (Vite)
- Streaming: RTSP → FastAPI → React UI
- Database: SQLite for events + permits

## Dev setup
### Backend
(I use powershell)
'''\Skytation
python -m venv .venv
MAY NEED THIS -> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000

### Frontend
(Open second powershell)
'''\Skytation
cd frontend
(install here -> https://nodejs.org/en/download)
npm install
npm run dev

Open: http://localhost:5173
