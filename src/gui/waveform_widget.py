import tkinter as tk
import customtkinter as ctk
import threading
import queue
import numpy as np
from typing import Optional
import sounddevice as sd


class WaveformWidget(ctk.CTkFrame):
    """
    Real-time audio oscilloscope display.
    Shows raw audio waveform (last ~0.1s) as a live line.
    Call start(mic_index) to begin monitoring, stop() to end.
    """

    FPS = 30
    WINDOW = 1600   # samples to display at once (~0.1s at 16 kHz)
    CHUNK = 512     # smaller chunk = more responsive

    def __init__(self, parent, height: int = 80, **kwargs):
        super().__init__(parent, fg_color="#0D0D0D", corner_radius=8, **kwargs)
        self.HEIGHT = height

        self._queue: queue.Queue = queue.Queue(maxsize=120)
        self._sample_buf = np.zeros(self.WINDOW, dtype=np.float32)
        self._running = False
        self._stream = None

        self._canvas = tk.Canvas(
            self, bg="#0D0D0D", highlightthickness=0,
            height=self.HEIGHT
        )
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._canvas.bind("<Configure>", self._on_resize)

        self._current_w = 400
        self._after_id = None
        self._draw_idle()

    # ── Public API ─────────────────────────────────────────────────────────

    def start(self, mic_index: Optional[int] = None):
        if self._running:
            self.stop()
        self._sample_buf[:] = 0
        self._running = True

        for device in ([mic_index, None] if mic_index is not None else [None]):
            try:
                self._stream = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype="float32",
                    blocksize=self.CHUNK,
                    device=device,
                    callback=self._audio_callback,
                )
                self._stream.start()
                break
            except Exception:
                self._stream = None
                if device is None:
                    self._running = False
                    return

        self._schedule_draw()

    def stop(self):
        self._running = False
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._sample_buf[:] = 0
        self._draw_idle()

    # ── Internal ───────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        try:
            self._queue.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass

    def _schedule_draw(self):
        if not self._running:
            return
        self._after_id = self.after(1000 // self.FPS, self._update)

    def _update(self):
        if not self._running:
            return
        # Drain all pending chunks
        while not self._queue.empty():
            try:
                chunk = self._queue.get_nowait()
                n = len(chunk)
                self._sample_buf = np.roll(self._sample_buf, -n)
                self._sample_buf[-n:] = chunk
            except queue.Empty:
                break

        self._draw_waveform()
        self._schedule_draw()

    def _on_resize(self, event):
        self._current_w = event.width
        if not self._running:
            self._draw_idle()

    def _draw_idle(self):
        c = self._canvas
        c.delete("all")
        w = self._current_w
        h = self.HEIGHT
        c.create_line(0, h // 2, w, h // 2, fill="#2A2A2A", width=1)
        c.create_text(w // 2, h // 2, text="마이크 비활성",
                      fill="#444", font=("Arial", 10))

    def _draw_waveform(self):
        c = self._canvas
        c.delete("all")
        w = self._current_w
        h = self.HEIGHT
        cy = h // 2

        # Background center line
        c.create_line(0, cy, w, cy, fill="#1A1A1A", width=1)

        samples = self._sample_buf
        n = len(samples)

        # Peak RMS for color
        rms = float(np.sqrt(np.mean(samples ** 2)))
        if rms < 0.03:
            color = "#00CC55"
        elif rms < 0.12:
            color = "#CCCC00"
        else:
            color = "#EE3322"

        # Build polyline points
        step = w / n
        pts = []
        for i, s in enumerate(samples):
            x = i * step
            y = cy - float(s) * (cy - 4)
            y = max(2, min(h - 2, y))
            pts.extend((x, y))

        if len(pts) >= 4:
            c.create_line(pts, fill=color, width=1, smooth=True)
