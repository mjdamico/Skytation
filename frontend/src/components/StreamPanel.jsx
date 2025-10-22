import { useEffect, useState } from 'react'

const BASE = 'http://127.0.0.1:8000'

export default function StreamPanel() {
  const [ok, setOk] = useState(true) // try mjpeg first
  const mjpeg = `${BASE}/api/video/mjpeg`
  const fallback = `${BASE}/media/sample.mp4`

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const r = await fetch(`${BASE}/api/video/health`)
        const j = await r.json()
        // Even if no RTSP, MJPEG endpoint returns placeholder, so ok can stay true.
        setOk(true)
      } catch {
        setOk(false)
      }
    }, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={{ display:'grid', gap:8 }}>
      {ok ? (
        <img
          src={mjpeg}
          alt="Live stream"
          onError={() => setOk(false)}
          style={{ width:'100%', maxWidth:900, border:'1px solid #333', borderRadius:12 }}
        />
      ) : (
        <video
          src={fallback}
          autoPlay
          muted
          loop
          controls
          style={{ width:'100%', maxWidth:900, border:'1px solid #333', borderRadius:12 }}
        />
      )}
      <div style={{ fontSize:12, opacity:.7 }}>
        {ok ? "Displaying MJPEG (live or placeholder)" : "Fallback sample video"}
      </div>
    </div>
  )
}
