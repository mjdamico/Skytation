import { useEffect, useState } from "react"

export default function App() {
  const [msg, setMsg] = useState("loading…")
  const [events, setEvents] = useState([])
  const [plate, setPlate] = useState("TEST123")

  useEffect(() => {
    fetch("http://localhost:8000/api/hello")
      .then(r => r.json()).then(d => setMsg(d.message))
      .catch(() => setMsg("backend not reachable"))

    reload()
    // websocket live updates
    const ws = new WebSocket("ws://localhost:8000/ws/events")
    ws.onmessage = (m) => {
      const ev = JSON.parse(m.data)
      setEvents(prev => [ev, ...prev])
    }
    return () => ws.close()
  }, [])

  const reload = () =>
    fetch("http://localhost:8000/api/events").then(r=>r.json()).then(setEvents)

  const seed = async () => {
    await fetch("http://localhost:8000/api/seed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate_text: plate, status: "UNKNOWN" })
    })
    reload()
  }

  return (
    <div style={{maxWidth: 720, margin: "3rem auto", fontFamily: "system-ui"}}>
      <h1>Frontend → FastAPI → SQLite</h1>
      <p>{msg}</p>

      <div style={{marginTop: 24}}>
        <input value={plate} onChange={e=>setPlate(e.target.value)} />
        <button onClick={seed} style={{marginLeft: 8}}>Add Test Event</button>
        <button onClick={reload} style={{marginLeft: 8}}>Reload</button>
      </div>

      <ul style={{marginTop: 16}}>
        {events.map(ev => (
          <li key={ev.id}>
            <b>{ev.plate_text}</b> — {ev.status} — {new Date(ev.ts).toLocaleString()}
          </li>
        ))}
      </ul>
      <small>(WebSocket will prepend new rows live)</small>
    </div>
  )
}
