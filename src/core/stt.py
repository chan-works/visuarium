import threading
import queue
import time
import os
import sys
import numpy as np
import sounddevice as sd
from typing import Callable, Optional


def _get_model_dir() -> str:
    """Return bundled model dir when frozen, else default cache."""
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'faster_whisper_models')
        if os.path.isdir(bundled):
            return bundled
    return os.path.join(os.path.expanduser('~'), '.cache', 'faster_whisper')


class STTEngine:
    def __init__(self, model_name: str = "base", mic_index: Optional[int] = None,
                 vad_threshold: float = 0.01, silence_duration: float = 1.5,
                 on_transcript: Optional[Callable[[str, float], None]] = None,
                 on_listening: Optional[Callable[[bool], None]] = None):
        self.model_name = model_name
        self.mic_index = mic_index
        self.vad_threshold = vad_threshold
        self.silence_duration = silence_duration
        self.on_transcript = on_transcript
        self.on_listening = on_listening

        self.model = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._thread = None
        self.sample_rate = 16000
        self.chunk_size = 1024

    def load_model(self, status_callback: Optional[Callable[[str], None]] = None):
        def _cb(msg):
            if status_callback:
                try:
                    status_callback(msg)
                except Exception:
                    pass

        _cb(f"Whisper 모델 로딩 중... ({self.model_name})")
        try:
            from faster_whisper import WhisperModel
            model_dir = _get_model_dir()
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",          # 가장 빠른 CPU 추론
                download_root=model_dir,
            )
            _cb("모델 로드 완료")
        except Exception as e:
            self.model = None
            _cb(f"모델 로드 실패: {e}")

    def start(self):
        if self._running:
            return
        if self.model is None:
            self.load_model()
        self._running = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def get_available_mics(self):
        devices = sd.query_devices()
        return [(i, d['name']) for i, d in enumerate(devices)
                if d['max_input_channels'] > 0]

    def _record_loop(self):
        buffer = []
        speaking = False
        silence_start = None
        speech_start = None

        def audio_callback(indata, frames, time_info, status):
            rms = float(np.sqrt(np.mean(indata ** 2)))
            self._audio_queue.put((indata.copy(), rms))

        # Try configured device, fall back to default if invalid
        stream_device = self.mic_index
        try:
            test = sd.InputStream(samplerate=self.sample_rate, channels=1,
                                   dtype='float32', blocksize=self.chunk_size,
                                   device=stream_device, callback=audio_callback)
            test.close()
        except Exception:
            stream_device = None

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=self.chunk_size,
            device=stream_device,
            callback=audio_callback,
        ):
            while self._running:
                try:
                    chunk, rms = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                is_voice = rms > self.vad_threshold

                if is_voice:
                    if not speaking:
                        speaking = True
                        speech_start = time.time()
                        if self.on_listening:
                            self.on_listening(True)
                    silence_start = None
                    buffer.append(chunk)
                else:
                    if speaking:
                        buffer.append(chunk)
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= self.silence_duration:
                            duration = time.time() - speech_start
                            if self.on_listening:
                                self.on_listening(False)
                            self._transcribe(buffer, duration)
                            buffer = []
                            speaking = False
                            silence_start = None
                            speech_start = None

    def _transcribe(self, buffer: list, duration: float):
        audio = np.concatenate(buffer, axis=0).flatten()
        try:
            segments, _ = self.model.transcribe(
                audio,
                beam_size=1,        # 빠른 추론 (greedy)
                language=None,      # 자동 언어 감지
                vad_filter=True,    # 내장 VAD로 묵음 구간 제거
            )
            text = " ".join(s.text for s in segments).strip()
            if text and self.on_transcript:
                self.on_transcript(text, duration)
        except Exception as e:
            print(f"[STT] 인식 오류: {e}")
