import tkinter as tk
import customtkinter as ctk
import threading
import queue
import numpy as np
from typing import Optional
import sounddevice as sd


class WaveformWidget(ctk.CTkFrame):
    """
    Real-time audio waveform display.
    Call start(mic_index) to begin monitoring, stop() to end.
    """

    WIDTH = 400
    HEIGHT = 80
    FPS = 30
    HISTORY = 300   # number of RMS samples to keep for the scrolling bar graph
    CHUNK = 1024

    def __init__(self, parent, height: int = 80, **kwargs):
        super().__init__(parent, fg_color="#0D0D0D", corner_radius=8, **kwargs)
        self.HEIGHT = height

        self._queue: queue.Queue = queue.Queue(maxsize=60)
        self._rms_history = np.zeros(self.HISTORY, dtype=np.float32)
        self._running = False
        self._stream = None
        self._mic_index: Optional[int] = None

        self._canvas = tk.Canvas(
            self, bg="#0D0D0D", highlightthickness=0,
            height=self.HEIGHT
        )
        self._canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._canvas.bind("<Configure>", self._on_resize)

        self._current_w = self.WIDTH
        self._after_id = None
        self._draw_idle()

    # ── Public API ─────────────────────────────────────────────────────────

    def start(self, mic_index: Optional[int] = None):
        if self._running:
            self.stop()
        self._mic_index = mic_index
        self._running = True
        self._stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="float32",
            blocksize=self.CHUNK,
            device=mic_index,
            callback=self._audio_callback,
        )
        self._stream.start()
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
        self._rms_history[:] = 0
        self._draw_idle()

    # ── Internal ───────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        try:
            self._queue.put_nowait(rms)
        except queue.Full:
            pass

    def _schedule_draw(self):
        if not self._running:
            return
        self._after_id = self.after(1000 // self.FPS, self._update)

    def _update(self):
        if not self._running:
            return
        # Drain queue into history
        new_samples = []
        while not self._queue.empty():
            try:
                new_samples.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if new_samples:
            n = len(new_samples)
            self._rms_history = np.roll(self._rms_history, -n)
            self._rms_history[-n:] = new_samples

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
        # Center line
        c.create_line(0, h // 2, w, h // 2, fill="#2A2A2A", width=1)
        c.create_text(w // 2, h // 2, text="마이크 비활성",
                      fill="#444", font=("Arial", 10))

    def _draw_waveform(self):
        c = self._canvas
        c.delete("all")
        w = self._current_w
        h = self.HEIGHT
        cy = h // 2

        # Background grid line
        c.create_line(0, cy, w, cy, fill="#1A1A1A", width=1)

        n = self.HISTORY
        bar_w = max(1, w / n)
        max_rms = 0.15   # clamp ceiling

        for i, rms in enumerate(self._rms_history):
            norm = min(rms / max_rms, 1.0)
            bar_h = norm * (cy - 4)
            if bar_h < 1:
                continue
            x = i * bar_w
            # Color: green → yellow → red based on amplitude
            if norm < 0.5:
                r = int(norm * 2 * 255)
                g = 220
            else:
                r = 220
                g = int((1 - (norm - 0.5) * 2) * 220)
            color = f"#{r:02x}{g:02x}44"
            c.create_rectangle(
                x, cy - bar_h, x + bar_w - 1, cy + bar_h,
                fill=color, outline=""
            )

        # Peak indicator line
        peak = float(np.max(self._rms_history))
        if peak > 0.005:
            norm_peak = min(peak / max_rms, 1.0)
            ph = norm_peak * (cy - 4)
            c.create_line(0, cy - ph, w, cy - ph, fill="#FFFFFF33", width=1)
