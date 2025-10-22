# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from .db import SessionLocal, Base, engine, Event, Permit, TimedStay, Violation

try:
    from .video import router as video_router
    HAS_VIDEO = True
except Exception:
    HAS_VIDEO = False


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def as_aware(dt: datetime | None) -> datetime:
    if dt is None:
        return utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------
# FastAPI Setup
# ---------------------------------------------------------------------
app = FastAPI(title="Skytation Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

if Path("media").exists():
    app.mount("/media", StaticFiles(directory="media"), name="media")

if HAS_VIDEO:
    app.include_router(video_router, prefix="/api/video")


# ---------------------------------------------------------------------
# Database dependency
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "service": "skytation"}


# ---------------------------------------------------------------------
# Event Schema
# ---------------------------------------------------------------------
class OCREventIn(BaseModel):
    plate_text: str
    confidence: float = Field(..., ge=0, le=1)
    timestamp: Optional[datetime] = None
    location: str = Field(..., pattern="^(permit|timed)$")
    image_hash: Optional[str] = None


CONF_THRESHOLD = 0.95
TIMED_LIMIT_MIN = 2  # for demo

# ---------------------------------------------------------------------
# Core OCR Event Decision Flow
# ---------------------------------------------------------------------
@app.post("/api/ocr_event")
def ocr_event(body: OCREventIn, db: Session = Depends(get_db)):
    ts = as_aware(body.timestamp)
    plate = body.plate_text.strip().upper()

    # 1. Confidence gate
    if body.confidence < CONF_THRESHOLD:
        ev = Event(
            plate_text=plate, confidence=body.confidence, timestamp=ts,
            location=body.location, result="violation", notes="low_confidence"
        )
        db.add(ev); db.commit()
        db.add(Violation(event_id=ev.id, plate_text=plate, timestamp=ts,
                         location=body.location, reason="low_confidence"))
        db.commit()
        return {"result": "violation", "reason": "low_confidence", "msg": "Confidence below threshold"}

    # 2. Permit Zone
    if body.location == "permit":
        match = db.query(Permit).filter(Permit.plate_text == plate).first()
        if match:
            ev = Event(
                plate_text=plate, confidence=body.confidence, timestamp=ts,
                location="permit", result="approved", notes="permit_found"
            )
            db.add(ev); db.commit()
            return {"result": "approved", "reason": "permit_found", "msg": "Permit approved"}
        else:
            ev = Event(
                plate_text=plate, confidence=body.confidence, timestamp=ts,
                location="permit", result="violation", notes="no_permit"
            )
            db.add(ev); db.commit()
            db.add(Violation(event_id=ev.id, plate_text=plate, timestamp=ts,
                             location="permit", reason="no_permit"))
            db.commit()
            return {"result": "violation", "reason": "no_permit", "msg": "No matching permit"}

    # 3. Timed Zone
    stay = db.query(TimedStay).filter(TimedStay.plate_text == plate).first()

    if not stay:
        # new timed entry
        stay = TimedStay(plate_text=plate, first_seen=ts, last_seen=ts)
        db.add(stay)
        db.commit()

        ev = Event(
            plate_text=plate, confidence=body.confidence, timestamp=ts,
            location="timed", result="approved", notes="timed_first_seen"
        )
        db.add(ev); db.commit()
        return {
            "result": "approved",
            "reason": "timed_first_seen",
            "msg": f"Started dwell timer for {plate}",
            "dwell_minutes": 0,
            "limit_minutes": TIMED_LIMIT_MIN
        }

    # existing entry → compute dwell time
    dwell = (ts - as_aware(stay.first_seen)).total_seconds() / 60
    stay.last_seen = ts
    db.commit()

    if dwell > TIMED_LIMIT_MIN:
        ev = Event(
            plate_text=plate, confidence=body.confidence, timestamp=ts,
            location="timed", result="violation", notes=f"exceeded_time:{dwell:.1f}m"
        )
        db.add(ev); db.commit()
        db.add(Violation(event_id=ev.id, plate_text=plate, timestamp=ts,
                         location="timed", reason="exceeded_time"))
        db.commit()
        return {
            "result": "violation",
            "reason": "exceeded_time",
            "msg": f"Exceeded time limit ({dwell:.1f} > {TIMED_LIMIT_MIN} min)",
            "dwell_minutes": dwell,
            "limit_minutes": TIMED_LIMIT_MIN
        }

    # still within limit
    ev = Event(
        plate_text=plate, confidence=body.confidence, timestamp=ts,
        location="timed", result="approved", notes=f"timed_ok:{dwell:.1f}m"
    )
    db.add(ev); db.commit()
    return {
        "result": "approved",
        "reason": "timed_ok",
        "msg": f"Within limit ({dwell:.1f}/{TIMED_LIMIT_MIN} min)",
        "dwell_minutes": dwell,
        "limit_minutes": TIMED_LIMIT_MIN
    }


# ---------------------------------------------------------------------
# Support Routes
# ---------------------------------------------------------------------
@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).limit(50).all()

@app.get("/api/violations")
def list_violations(db: Session = Depends(get_db)):
    return db.query(Violation).order_by(Violation.id.desc()).limit(50).all()

@app.post("/api/permits/seed")
def seed_permits(db: Session = Depends(get_db)):
    sample = ["ABC123", "XYZ789", "PURDUE1"]
    for p in sample:
        if not db.query(Permit).filter(Permit.plate_text == p).first():
            db.add(Permit(plate_text=p, permit_type="A"))
    db.commit()
    return {"seeded": sample}

@app.post("/api/timed/reset")
def reset_timed(db: Session = Depends(get_db)):
    db.query(TimedStay).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/timed_stays")
def get_timed_stays(db: Session = Depends(get_db)):
    return db.query(TimedStay).all()

@app.get("/api/permits")
def get_permits(db: Session = Depends(get_db)):
    return db.query(Permit).all()

@app.get("/api/violations")
def get_violations(db: Session = Depends(get_db)):
    return db.query(Violation).all()

# ---------------------------------------------------------------------
# WebSocket for live UI updates
# ---------------------------------------------------------------------
class WSManager:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, payload: dict):
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(ws)

ws_manager = WSManager()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
