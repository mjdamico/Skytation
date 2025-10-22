import { useEffect, useState, useCallback } from "react";
import StreamPanel from "./components/StreamPanel.jsx";

const API = "http://127.0.0.1:8000/api";
const WS_URL = "ws://127.0.0.1:8000/ws";

export default function App() {
  const [status, setStatus] = useState("checking…");
  const [events, setEvents] = useState([]);
  const [plate, setPlate] = useState("TEST123");
  const [decisionMsg, setDecisionMsg] = useState("");
  const [decisionColor, setDecisionColor] = useState("#1a1a1a"); // green/red bg

  const reload = useCallback(async () => {
    const r = await fetch(`${API}/events?limit=100`);
    setEvents(await r.json());
  }, []);

  useEffect(() => {
    // health
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(() => setStatus("backend ok"))
      .catch(() => setStatus("backend not reachable"));

    // initial events
    reload();

    // websocket live updates
    const ws = new WebSocket(WS_URL);
    ws.onmessage = () => reload();
    return () => ws.close();
  }, [reload]);

  const addTestEvent = async () => {
    await fetch(`${API}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plate_text: plate,
        type: "timed",
      }),
    });
    await reload();
  };

  const removeLast = async () => {
    await fetch(`${API}/events/last`, { method: "DELETE" });
    await reload();
  };

  const seedPermits = async () => {
    await fetch(`${API}/permits/seed`, { method: "POST" });
  };

  const resetTimed = async () => {
    await fetch(`${API}/timed/reset`, { method: "POST" });
  };

  const submitOCREvent = async () => {
    const conf = parseFloat(document.getElementById("confField").value || "0.99");
    const loc = document.querySelector('input[name="loc"]:checked').value;

    const payload = {
      plate_text: plate,
      confidence: conf,
      timestamp: new Date().toISOString(),
      location: loc,
      image_hash: null,
    };

    const r = await fetch(`${API}/ocr_event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const decision = await r.json();
    const ok = decision.result === "approved";
    setDecisionMsg(decision.message);
    setDecisionColor(ok ? "#1b5e20" : "#7f1d1d"); // green / red
    await reload();
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#111",
        color: "#eee",
        fontFamily: "Inter, system-ui, Arial",
      }}
    >
      <header style={{ padding: "20px 28px 0" }}>
        <h1 style={{ fontSize: 42, margin: 0 }}>Frontend → FastAPI → SQLite</h1>
        <div style={{ opacity: 0.8, marginTop: 6 }}>{status}</div>
      </header>

      {/* Two-column layout */}
      <main
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr", // ~two-thirds / one-third
          gap: 24,
          padding: "20px 28px 28px",
          alignItems: "start",
        }}
      >
        {/* Left: video takes ~two-thirds width */}
        <section style={{ width: "100%" }}>
          <div
            style={{
              width: "100%",
              maxWidth: "1600px",
              aspectRatio: "16/9",
              display: "block",
            }}
          >
            <StreamPanel />
          </div>
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 6 }}>
            If RTSP isn’t configured, this shows the fallback sample video.
          </div>
        </section>

        {/* Right: controls + events list */}
        <aside>
          {/* Decision banner */}
          <div
            style={{
              display: decisionMsg ? "block" : "none",
              background: decisionColor,
              border: "1px solid #333",
              borderRadius: 10,
              padding: "10px 12px",
              fontWeight: 600,
              textAlign: "center",
              marginBottom: 12,
            }}
          >
            {decisionMsg}
          </div>

          {/* OCR Event form */}
          <div
            style={{
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: 12,
              padding: 16,
              marginBottom: 16,
            }}
          >
            <h3 style={{ marginTop: 0 }}>Submit OCR Event (demo)</h3>
            <div style={{ display: "grid", gap: 10 }}>
              <label>
                Plate
                <input
                  value={plate}
                  onChange={(e) => setPlate(e.target.value)}
                  placeholder="plate"
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: "1px solid #444",
                    background: "#222",
                    color: "#eee",
                    marginTop: 4,
                  }}
                />
              </label>

              <label>
                Confidence (0..1)
                <input
                  defaultValue={0.99}
                  id="confField"
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: "1px solid #444",
                    background: "#222",
                    color: "#eee",
                    marginTop: 4,
                  }}
                />
              </label>

              <div>
                Location
                <div style={{ display: "flex", gap: 12, marginTop: 6 }}>
                  <label>
                    <input type="radio" name="loc" value="permit" defaultChecked /> Permit
                  </label>
                  <label>
                    <input type="radio" name="loc" value="timed" /> Timed
                  </label>
                </div>
              </div>

              <button
                onClick={submitOCREvent}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #555",
                  background: "#2962ff",
                  color: "#fff",
                  width: "100%",
                }}
              >
                Submit OCR Event
              </button>
            </div>
          </div>

          {/* Quick demo helpers */}
          <div
            style={{
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: 12,
              padding: 16,
              marginBottom: 16,
              display: "grid",
              gap: 8,
            }}
          >
            <button
              onClick={seedPermits}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid #555",
                background: "#2e7d32",
                color: "#fff",
              }}
            >
              Seed Permits
            </button>
            <button
              onClick={resetTimed}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid #555",
                background: "#424242",
                color: "#fff",
              }}
            >
              Reset Timed Stays
            </button>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={addTestEvent}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #555",
                  background: "#00695c",
                  color: "#fff",
                }}
              >
                Add Raw Test Event
              </button>
              <button
                onClick={removeLast}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #555",
                  background: "#b71c1c",
                  color: "#fff",
                }}
              >
                Remove Last Event
              </button>
              <button
                onClick={reload}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid #555",
                  background: "#424242",
                  color: "#fff",
                }}
              >
                Reload
              </button>
            </div>
          </div>

          {/* Events list */}
          <div
            style={{
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: 12,
              padding: 16,
              maxHeight: "70vh",
              overflow: "auto",
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: 8 }}>Recent Events</h3>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {events.map((ev) => (
                <li key={ev.id} style={{ marginBottom: 6 }}>
                  <b>{ev.license_plate_number ?? ev.plate_text}</b>{" "}
                  <span style={{ opacity: 0.8 }}>
                    — {ev.type ?? ev.status ?? "event"}
                    {typeof ev.flagged === "boolean"
                      ? ev.flagged
                        ? " (violation)"
                        : " (approved)"
                      : ""}{" "}
                    — {ev.created_at
                      ? new Date(ev.created_at).toLocaleString()
                      : ev.ts
                      ? new Date(ev.ts).toLocaleString()
                      : ""}
                  </span>
                  {ev.notes ? <span style={{ opacity: 0.7 }}> — {ev.notes}</span> : null}
                </li>
              ))}
            </ul>
            <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
              WebSocket refreshes this list automatically.
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
