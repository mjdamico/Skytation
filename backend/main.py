from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .db import SessionLocal, Event
from fastapi import HTTPException

app = FastAPI()

# CORS (we’ll add a Vite proxy later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB session dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root(): return {"ok": True}

@app.get("/api/hello")
def hello(): return {"message": "Hello from FastAPI backend!"}

# --- Events API ---
@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).limit(20).all()

class SeedIn(BaseModel):
    plate_text: str
    status: str = "UNKNOWN"

@app.post("/api/seed")
def seed_one(body: SeedIn, db: Session = Depends(get_db)):
    ev = Event(plate_text=body.plate_text, status=body.status)
    db.add(ev); db.commit(); db.refresh(ev)
    # also push over websocket if clients connected
    for c in list(clients):
        try: import anyio; anyio.from_thread.run(send_json, c, ev)
        except: pass
    return ev

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(Event).filter(Event.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(ev)
    db.commit()
    return {"ok": True, "deleted_id": event_id}

# --- WebSocket for live events ---
clients: set[WebSocket] = set()

@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()   # optional keep-alive
    except WebSocketDisconnect:
        clients.discard(ws)

# helper to send JSON for SQLAlchemy objects
async def send_json(ws: WebSocket, ev: Event):
    await ws.send_json({
        "id": ev.id,
        "plate_text": ev.plate_text,
        "status": ev.status,
        "ts": ev.ts.isoformat() if ev.ts else None
    })
