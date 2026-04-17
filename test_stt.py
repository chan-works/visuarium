"""
STT 테스트 스크립트 — 실행하면 5초 동안 녹음 후 Whisper로 인식
사용법: python test_stt.py
"""
import numpy as np
import sounddevice as sd
import time

SAMPLE_RATE = 16000
DURATION = 5  # 초

def test_mic():
    print("=== 마이크 목록 ===")
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            print(f"  [{i}] {d['name']}")
    print()

def test_stt():
    print(f"=== {DURATION}초 동안 녹음합니다. 한국어로 말해보세요 ===")
    audio = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE,
                   channels=1, dtype='float32', device=None)

    for i in range(DURATION, 0, -1):
        print(f"  {i}초 남음...", end="\r")
        time.sleep(1)

    sd.wait()
    print(f"\n녹음 완료. RMS = {float(np.sqrt(np.mean(audio**2))):.5f}")

    print("\n=== Whisper 인식 중... ===")
    t0 = time.time()

    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")

    audio_flat = audio.flatten()
    segments, info = model.transcribe(
        audio_flat,
        beam_size=1,
        language="ko",
        vad_filter=False,
        no_speech_threshold=0.6,
    )

    text = "".join(s.text for s in segments).strip()
    elapsed = time.time() - t0

    print(f"감지된 언어: {info.language} (확률: {info.language_probability:.2f})")
    print(f"인식 결과: '{text}'")
    print(f"소요 시간: {elapsed:.2f}초")

if __name__ == "__main__":
    test_mic()
    test_stt()
