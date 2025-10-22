# backend/video.py
import threading, time
from typing import Optional
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fastapi import APIRouter, Response
from starlette.responses import StreamingResponse, JSONResponse

router = APIRouter(prefix="/video", tags=["video"])

DEFAULT_RTSP_URL = None  # None means "no camera yet"

class RTSPStreamer:
    def __init__(self, url: Optional[str] = DEFAULT_RTSP_URL):
        self.url = url
        self.cap = None
        self.running = False
        self.lock = threading.Lock()
        self.last_jpeg = None  # bytes
        self.thread = None

    def start(self):
        with self.lock:
            if self.running or not self.url:
                return
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    def set_url(self, url: Optional[str]):
        with self.lock:
            self.url = url
        self.stop()
        if url:
            self.start()

    def _open(self):
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG if self.url and self.url.startswith("rtsp") else 0)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _loop(self):
        try:
            self._open()
            if not self.cap or not self.cap.isOpened():
                # mark not running if failed
                self.stop()
                return
            while self.running:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                # optionally resize to reduce bandwidth
                h, w = frame.shape[:2]
                if w > 1280:
                    frame = cv2.resize(frame, (1280, int(1280*h/w)))
                # BGR -> JPEG
                ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    self.last_jpeg = jpg.tobytes()
        except Exception:
            pass
        finally:
            self.stop()

    def health(self):
        return {"url": self.url, "running": self.running, "has_frame": self.last_jpeg is not None}

streamer = RTSPStreamer()

def _placeholder_jpeg(text="RTSP not configured"):
    img = Image.new("RGB", (960, 540), "#202020")
    d = ImageDraw.Draw(img)
    info = [
        "Skytation — MJPEG preview",
        text,
        "Set RTSP URL later; UI will switch automatically."
    ]
    y = 200
    for line in info:
        d.text((80, y), line, fill="#f0f0f0")
        y += 36
    arr = np.array(img)[:, :, ::-1]  # to BGR for cv2
    ok, jpg = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return jpg.tobytes() if ok else b""

@router.get("/health")
def video_health():
    return JSONResponse(streamer.health())

@router.post("/set_url")
def set_url(url: Optional[str] = None):
    streamer.set_url(url)
    return JSONResponse({"ok": True, **streamer.health()})

@router.get("/mjpeg")
def mjpeg_stream():
    """
    Multipart MJPEG stream. Works in <img> src and updates live.
    """
    boundary = "frame"
    def gen():
        # ensure started if we have a url
        streamer.start()
        while True:
            frame = streamer.last_jpeg or _placeholder_jpeg()
            yield (b"--" + boundary.encode() + b"\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" +
                   frame + b"\r\n")
            time.sleep(0.05)  # ~20 fps
    return StreamingResponse(gen(), media_type=f"multipart/x-mixed-replace; boundary={boundary}")
