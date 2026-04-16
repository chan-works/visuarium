import customtkinter as ctk
import threading
import time
from typing import Callable, Optional
from src.core.agent import VisuariumAgent
from src.core.stt import STTEngine
from src.core import database


PROMPT_GUIDE = """🎨 프롬프트 가이드

1️⃣  Subject (주제)
    무엇이 등장하나요?
    예: 로봇, 고양이, 아이언맨, 소녀

2️⃣  Environment (환경/배경)
    어떤 공간/배경인가요?
    예: 우주, 숲, 미래 도시, 밤바다

3️⃣  Style (스타일)
    어떤 예술 스타일인가요?
    예: 반 고흐, 수채화, 사이버펑크

4️⃣  Mood & Color (분위기/색감)
    어떤 감정/분위기와 색인가요?
    예: 신비롭고 보라색, 따뜻한 황금빛

💡 짧게 말해도 괜찮아요!
   AI가 질문하며 프롬프트를 함께 만들어드립니다."""


class SessionPanel(ctk.CTkFrame):
    def __init__(self, parent, config: dict,
                 on_prompt_ready: Callable[[str], None],
                 **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.on_prompt_ready = on_prompt_ready

        self.session_id: Optional[int] = None
        self.utterance_index = 0
        self.session_active = False
        self.total_duration = 0.0
        self._timer_thread: Optional[threading.Thread] = None
        self._session_start_time: Optional[float] = None

        self.agent = VisuariumAgent(
            api_key=config.get("api_key", ""),
            model=config.get("model", "claude-opus-4-6")
        )
        self.stt = STTEngine(
            model_name=config.get("whisper_model", "base"),
            mic_index=config.get("mic_index"),
            vad_threshold=config.get("vad_threshold", 0.01),
            silence_duration=config.get("silence_duration", 1.5),
            on_transcript=self._on_transcript,
            on_listening=self._on_listening,
        )

        self._build()
        self._load_model()

    def _build(self):
        # ── Top status bar ─────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=8)
        top.pack(fill="x", padx=16, pady=(12, 6))

        self.status_label = ctk.CTkLabel(top, text="● 대기 중",
                                          font=ctk.CTkFont(size=13), text_color="#888")
        self.status_label.pack(side="left", padx=12, pady=8)

        self.timer_label = ctk.CTkLabel(top, text="총 발화 시간: 0.0초",
                                         font=ctk.CTkFont(size=12), text_color="#888")
        self.timer_label.pack(side="right", padx=12)

        # ── Session control buttons ────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶ 세션 시작", width=140,
            fg_color="#2ECC71", hover_color="#27AE60",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_session
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_row, text="■ 세션 종료", width=140,
            fg_color="#E74C3C", hover_color="#C0392B",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self.stop_session
        )
        self.stop_btn.pack(side="left")

        self.session_label = ctk.CTkLabel(btn_row, text="세션 없음",
                                           font=ctk.CTkFont(size=12), text_color="#888")
        self.session_label.pack(side="right", padx=8)

        # ── Main content: guide + conversation ────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # Left: prompt guide
        guide_frame = ctk.CTkFrame(content, fg_color="#1E1E1E", corner_radius=10)
        guide_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        guide_label = ctk.CTkLabel(guide_frame, text=PROMPT_GUIDE,
                                    font=ctk.CTkFont(family="Malgun Gothic", size=12),
                                    justify="left", anchor="nw", wraplength=240)
        guide_label.pack(fill="both", expand=True, padx=14, pady=12)

        # Right: conversation
        conv_frame = ctk.CTkFrame(content, fg_color="#1E1E1E", corner_radius=10)
        conv_frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(conv_frame, text="대화",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#A0C4E4").pack(anchor="w", padx=12, pady=(10, 4))

        self.chat_box = ctk.CTkTextbox(conv_frame, state="disabled",
                                        font=ctk.CTkFont(family="Malgun Gothic", size=12),
                                        fg_color="#141414", text_color="white",
                                        wrap="word")
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # ── Current prompt display ─────────────────────────────────────────
        prompt_frame = ctk.CTkFrame(self, fg_color="#0D2137", corner_radius=8)
        prompt_frame.pack(fill="x", padx=16, pady=(6, 12))

        ctk.CTkLabel(prompt_frame, text="현재 프롬프트",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#A0C4E4").pack(anchor="w", padx=12, pady=(8, 2))
        self.prompt_label = ctk.CTkLabel(
            prompt_frame, text="(아직 프롬프트 없음)",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#E8E8E8", wraplength=600, justify="left", anchor="w"
        )
        self.prompt_label.pack(fill="x", padx=12, pady=(0, 8))

        self._append_chat("시스템", "Whisper 모델을 로딩 중입니다...")

    def _load_model(self):
        self.start_btn.configure(state="disabled")

        def _load():
            def _status(msg):
                self.after(0, lambda m=msg: self._set_status(m))
                self.after(0, lambda m=msg: self._append_chat("시스템", m))

            self.stt.load_model(status_callback=_status)

            if self.stt.model is not None:
                self.after(0, lambda: self.start_btn.configure(state="normal"))
                self.after(0, lambda: self._set_status("● 대기 중 (시작 버튼을 눌러주세요)", "#888888"))
            else:
                self.after(0, lambda: self._set_status("⚠ 모델 로드 실패 — 설정에서 Whisper 모델을 확인하세요", "#E74C3C"))

        threading.Thread(target=_load, daemon=True).start()

    def _set_status(self, text: str, color: str = "#888888"):
        self.after(0, lambda: self.status_label.configure(text=text, text_color=color))

    def start_session(self):
        if not self.config.get("api_key"):
            self._append_chat("⚠ 오류", "API Key가 설정되지 않았습니다. [설정] 탭에서 입력해 주세요.")
            return

        self.session_id = database.create_session()
        self.utterance_index = 0
        self.total_duration = 0.0
        self.agent.reset()
        self.session_active = True
        self._session_start_time = time.time()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.session_label.configure(text=f"세션 #{self.session_id}", text_color="#2ECC71")
        self._set_status("● 듣는 중", "#2ECC71")

        self.stt.start()
        self._start_timer()

        for tag in self.chat_box.tag_names():
            self.chat_box.tag_delete(tag)
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self._append_chat("시스템", "세션이 시작되었습니다. 마이크에 대고 말씀해 주세요!")

    def stop_session(self):
        self.session_active = False
        self.stt.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._set_status("● 대기 중", "#888888")
        self._append_chat("시스템", f"세션 종료. 총 발화 횟수: {self.utterance_index}회, "
                                    f"총 시간: {self.total_duration:.1f}초")

    def _start_timer(self):
        def update():
            while self.session_active:
                self.after(0, lambda: self.timer_label.configure(
                    text=f"총 발화 시간: {self.total_duration:.1f}초"
                ))
                time.sleep(0.5)
        threading.Thread(target=update, daemon=True).start()

    def _on_listening(self, is_speaking: bool):
        if is_speaking:
            self._set_status("🔴 음성 감지 중...", "#E74C3C")
        else:
            if self.session_active:
                self._set_status("● 듣는 중", "#2ECC71")

    def _on_transcript(self, text: str, duration: float):
        if not self.session_active:
            return
        self.total_duration += duration
        self.utterance_index += 1
        idx = self.utterance_index

        self._append_chat(f"👤 관객 #{idx}", text)
        self._set_status("⏳ AI 응답 생성 중...", "#F39C12")

        def _call_agent():
            try:
                display, prompt = self.agent.chat(text)
                database.save_utterance(
                    session_id=self.session_id,
                    utterance_index=idx,
                    utterance_text=text,
                    prompt_text=prompt,
                    duration_sec=duration,
                )
                self.after(0, lambda: self._on_agent_response(display, prompt))
            except Exception as e:
                self.after(0, lambda: self._append_chat("⚠ 오류", str(e)))
                self.after(0, lambda: self._set_status("● 듣는 중", "#2ECC71"))

        threading.Thread(target=_call_agent, daemon=True).start()

    def _on_agent_response(self, display: str, prompt: str):
        self._append_chat("🤖 AI", display)
        self.prompt_label.configure(text=prompt)
        self.on_prompt_ready(prompt)
        if self.session_active:
            self._set_status("● 듣는 중", "#2ECC71")

    def _append_chat(self, speaker: str, text: str):
        def _do():
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"\n[{speaker}]\n", "speaker")
            self.chat_box.insert("end", f"{text}\n")
            self.chat_box.configure(state="disabled")
            self.chat_box.see("end")
        self.after(0, _do)

    def update_config(self, config: dict):
        self.config = config
        self.agent.update_api_key(config.get("api_key", ""))
        self.agent.model = config.get("model", "claude-opus-4-6")
        self.stt.mic_index = config.get("mic_index")
        self.stt.vad_threshold = config.get("vad_threshold", 0.01)
        self.stt.silence_duration = config.get("silence_duration", 1.5)
