import customtkinter as ctk
import json
import os
import threading
import sounddevice as sd
from typing import Callable
from src.gui.waveform_widget import WaveformWidget
from src.core.osc_sender import OSCSender

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, parent, config: dict, on_save: Callable[[dict], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.on_save = on_save
        self._waveform: WaveformWidget = None
        self._mic_testing = False
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="⚙ 설정", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(16, 10), padx=20, anchor="w")

        # ── API Provider ────────────────────────────────────────────────────
        section = self._section("AI 제공자")

        row_p = ctk.CTkFrame(section, fg_color="transparent")
        row_p.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(row_p, text="제공자").pack(side="left")
        self.provider_var = ctk.StringVar(value=self.config.get("provider", "Claude"))
        provider_menu = ctk.CTkOptionMenu(
            row_p, variable=self.provider_var,
            values=["Claude", "OpenAI"],
            command=self._on_provider_change
        )
        provider_menu.pack(side="left", padx=(8, 0))

        # Claude section
        self._claude_frame = ctk.CTkFrame(section, fg_color="transparent")
        self._claude_frame.pack(fill="x")

        ctk.CTkLabel(self._claude_frame, text="Claude API Key").pack(anchor="w")
        self.claude_key_entry = ctk.CTkEntry(self._claude_frame, width=380, show="*",
                                              placeholder_text="sk-ant-api...")
        self.claude_key_entry.pack(fill="x", pady=(0, 4))
        self.claude_key_entry.insert(0, self.config.get("claude_api_key", self.config.get("api_key", "")))

        row_cm = ctk.CTkFrame(self._claude_frame, fg_color="transparent")
        row_cm.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row_cm, text="모델").pack(side="left")
        self.claude_model_var = ctk.StringVar(value=self.config.get("claude_model", "claude-opus-4-6"))
        ctk.CTkOptionMenu(row_cm, variable=self.claude_model_var,
                          values=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"]
                          ).pack(side="left", padx=(8, 0))

        # OpenAI section
        self._openai_frame = ctk.CTkFrame(section, fg_color="transparent")
        self._openai_frame.pack(fill="x")

        ctk.CTkLabel(self._openai_frame, text="OpenAI API Key").pack(anchor="w")
        self.openai_key_entry = ctk.CTkEntry(self._openai_frame, width=380, show="*",
                                              placeholder_text="sk-...")
        self.openai_key_entry.pack(fill="x", pady=(0, 4))
        self.openai_key_entry.insert(0, self.config.get("openai_api_key", ""))

        row_om = ctk.CTkFrame(self._openai_frame, fg_color="transparent")
        row_om.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row_om, text="모델").pack(side="left")
        self.openai_model_var = ctk.StringVar(value=self.config.get("openai_model", "gpt-5.4"))
        ctk.CTkOptionMenu(row_om, variable=self.openai_model_var,
                          values=["gpt-5.4", "gpt-5-4-mini", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
                          ).pack(side="left", padx=(8, 0))

        self._on_provider_change(self.provider_var.get())

        # ── Microphone ─────────────────────────────────────────────────────
        section2 = self._section("마이크 설정")
        ctk.CTkLabel(section2, text="마이크 선택").pack(anchor="w")
        self._mic_options = self._get_mic_options()
        self.mic_var = ctk.StringVar(value=self.config.get("mic_name", "기본 장치"))
        self.mic_menu = ctk.CTkOptionMenu(section2, variable=self.mic_var,
                                           values=list(self._mic_options.keys()),
                                           command=self._on_mic_change)
        self.mic_menu.pack(fill="x", pady=(0, 6))

        # Waveform test
        ctk.CTkLabel(section2, text="마이크 테스트",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(anchor="w")
        self._waveform = WaveformWidget(section2, height=64)
        self._waveform.pack(fill="x", pady=(2, 6))

        self._test_btn = ctk.CTkButton(
            section2, text="▶ 테스트 시작", width=120, height=26,
            fg_color="#2C5F8A", hover_color="#1E4060",
            font=ctk.CTkFont(size=12),
            command=self._toggle_mic_test
        )
        self._test_btn.pack(anchor="w")

        # VAD / Silence
        row2 = ctk.CTkFrame(section2, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(row2, text="VAD 임계값").pack(side="left")
        self.vad_entry = ctk.CTkEntry(row2, width=70)
        self.vad_entry.insert(0, str(self.config.get("vad_threshold", 0.01)))
        self.vad_entry.pack(side="left", padx=(8, 16))
        ctk.CTkLabel(row2, text="묵음 판정(초)").pack(side="left")
        self.silence_entry = ctk.CTkEntry(row2, width=70)
        self.silence_entry.insert(0, str(self.config.get("silence_duration", 1.5)))
        self.silence_entry.pack(side="left", padx=(8, 0))

        # Whisper model
        row3 = ctk.CTkFrame(section2, fg_color="transparent")
        row3.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row3, text="Whisper 모델").pack(side="left")
        self.whisper_var = ctk.StringVar(value=self.config.get("whisper_model", "base"))
        ctk.CTkOptionMenu(row3, variable=self.whisper_var,
                          values=["tiny", "base", "small", "medium", "large"]
                          ).pack(side="left", padx=(8, 0))

        # ── OSC ────────────────────────────────────────────────────────────
        section3 = self._section("OSC 설정")
        row4 = ctk.CTkFrame(section3, fg_color="transparent")
        row4.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row4, text="IP").pack(side="left")
        self.osc_ip_entry = ctk.CTkEntry(row4, width=130)
        self.osc_ip_entry.insert(0, self.config.get("osc_ip", "127.0.0.1"))
        self.osc_ip_entry.pack(side="left", padx=(8, 16))
        ctk.CTkLabel(row4, text="Port").pack(side="left")
        self.osc_port_entry = ctk.CTkEntry(row4, width=80)
        self.osc_port_entry.insert(0, str(self.config.get("osc_port", 9001)))
        self.osc_port_entry.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(section3, text="OSC Address").pack(anchor="w")
        self.osc_addr_entry = ctk.CTkEntry(section3)
        self.osc_addr_entry.insert(0, self.config.get("osc_address", "/visuarium/prompt"))
        self.osc_addr_entry.pack(fill="x", pady=(0, 4))

        row5 = ctk.CTkFrame(section3, fg_color="transparent")
        row5.pack(fill="x")
        ctk.CTkLabel(row5, text="WebSocket Port").pack(side="left")
        self.ws_port_entry = ctk.CTkEntry(row5, width=80)
        self.ws_port_entry.insert(0, str(self.config.get("websocket_port", 9000)))
        self.ws_port_entry.pack(side="left", padx=(8, 0))

        # ── OSC 테스트 ─────────────────────────────────────────────────────
        section4 = self._section("OSC 전송 테스트")

        ctk.CTkLabel(section4, text="테스트 메시지").pack(anchor="w")
        self.osc_test_entry = ctk.CTkEntry(section4, placeholder_text="전송할 텍스트 입력...")
        self.osc_test_entry.insert(0, "a beautiful rose blooming at night")
        self.osc_test_entry.pack(fill="x", pady=(0, 6))

        test_row = ctk.CTkFrame(section4, fg_color="transparent")
        test_row.pack(fill="x")

        self._osc_test_btn = ctk.CTkButton(
            test_row, text="▶ OSC 전송", width=110, height=28,
            fg_color="#2C5F8A", hover_color="#1E4060",
            font=ctk.CTkFont(size=12),
            command=self._send_osc_test
        )
        self._osc_test_btn.pack(side="left")

        self._osc_status = ctk.CTkLabel(
            test_row, text="", font=ctk.CTkFont(size=12),
            text_color="#888", anchor="w"
        )
        self._osc_status.pack(side="left", padx=(12, 0))

        # ── Save button ────────────────────────────────────────────────────
        save_btn = ctk.CTkButton(self, text="저장", command=self._save,
                                  fg_color="#2ECC71", hover_color="#27AE60",
                                  font=ctk.CTkFont(size=14, weight="bold"))
        save_btn.pack(pady=16, padx=20, fill="x")

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack()

    # ── Provider toggle ────────────────────────────────────────────────────

    def _on_provider_change(self, value: str):
        if value == "Claude":
            self._claude_frame.pack(fill="x")
            self._openai_frame.pack_forget()
        else:
            self._claude_frame.pack_forget()
            self._openai_frame.pack(fill="x")

    # ── Mic test ───────────────────────────────────────────────────────────

    def _toggle_mic_test(self):
        if self._mic_testing:
            self._waveform.stop()
            self._mic_testing = False
            self._test_btn.configure(text="▶ 테스트 시작", fg_color="#2C5F8A")
        else:
            mic_index = self._mic_options.get(self.mic_var.get())
            try:
                self._waveform.start(mic_index)
                self._mic_testing = True
                self._test_btn.configure(text="■ 테스트 중지", fg_color="#8A2C2C")
            except Exception as e:
                self.status_label.configure(text="마이크 오류 (기본 장치로 재시도됨)", text_color="#F39C12")

    def _on_mic_change(self, _):
        if self._mic_testing:
            self._waveform.stop()
            mic_index = self._mic_options.get(self.mic_var.get())
            try:
                self._waveform.start(mic_index)
            except Exception:
                pass

    # ── Helpers ────────────────────────────────────────────────────────────

    def _section(self, title: str) -> ctk.CTkFrame:
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#A0C4E4").pack(anchor="w", padx=20, pady=(10, 2))
        frame = ctk.CTkFrame(self, fg_color="#2B2B2B", corner_radius=8)
        frame.pack(fill="x", padx=20, pady=(0, 4))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        return inner

    def _get_mic_options(self) -> dict:
        options = {"기본 장치": None}
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    options[f"[{i}] {d['name']}"] = i
        except Exception:
            pass
        return options

    def _send_osc_test(self):
        msg = self.osc_test_entry.get().strip()
        if not msg:
            self._osc_status.configure(text="⚠ 메시지를 입력하세요", text_color="#F39C12")
            return

        ip = self.osc_ip_entry.get().strip()
        try:
            port = int(self.osc_port_entry.get().strip())
        except ValueError:
            self._osc_status.configure(text="⚠ Port가 올바르지 않습니다", text_color="#E74C3C")
            return
        address = self.osc_addr_entry.get().strip()

        self._osc_test_btn.configure(state="disabled")
        self._osc_status.configure(text="전송 중...", text_color="#888")

        def _do():
            try:
                sender = OSCSender(ip=ip, port=port, address=address)
                sender.send_prompt(msg)
                self.after(0, lambda: self._osc_status.configure(
                    text=f"✓ 전송 완료  →  {ip}:{port}  {address}", text_color="#2ECC71"))
            except Exception as e:
                self.after(0, lambda err=e: self._osc_status.configure(
                    text=f"✗ 전송 실패: {err}", text_color="#E74C3C"))
            finally:
                self.after(0, lambda: self._osc_test_btn.configure(state="normal"))
                self.after(3000, lambda: self._osc_status.configure(text=""))

        threading.Thread(target=_do, daemon=True).start()

    def _save(self):
        if self._mic_testing:
            self._waveform.stop()
            self._mic_testing = False
            self._test_btn.configure(text="▶ 테스트 시작", fg_color="#2C5F8A")

        try:
            provider = self.provider_var.get()
            mic_name = self.mic_var.get()
            mic_index = self._mic_options.get(mic_name)

            # Active API key & model based on provider
            if provider == "Claude":
                active_api_key = self.claude_key_entry.get().strip()
                active_model = self.claude_model_var.get()
            else:
                active_api_key = self.openai_key_entry.get().strip()
                active_model = self.openai_model_var.get()

            new_config = {
                "provider": provider,
                "api_key": active_api_key,       # active key (for legacy compat)
                "model": active_model,            # active model
                "claude_api_key": self.claude_key_entry.get().strip(),
                "claude_model": self.claude_model_var.get(),
                "openai_api_key": self.openai_key_entry.get().strip(),
                "openai_model": self.openai_model_var.get(),
                "mic_index": mic_index,
                "mic_name": mic_name,
                "osc_ip": self.osc_ip_entry.get().strip(),
                "osc_port": int(self.osc_port_entry.get().strip()),
                "osc_address": self.osc_addr_entry.get().strip(),
                "websocket_port": int(self.ws_port_entry.get().strip()),
                "whisper_model": self.whisper_var.get(),
                "vad_threshold": float(self.vad_entry.get().strip()),
                "silence_duration": float(self.silence_entry.get().strip()),
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
            self.config.update(new_config)
            self.on_save(new_config)
            self.status_label.configure(text="✓ 저장 완료", text_color="#2ECC71")
            self.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.status_label.configure(text=f"오류: {e}", text_color="#E74C3C")
