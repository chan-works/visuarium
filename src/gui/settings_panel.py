import customtkinter as ctk
import json
import os
import sounddevice as sd
from typing import Callable

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, parent, config: dict, on_save: Callable[[dict], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.on_save = on_save
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="⚙ 설정", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(16, 10), padx=20, anchor="w")

        # ── API Key ────────────────────────────────────────────────────────
        section = self._section("Claude API")
        ctk.CTkLabel(section, text="API Key").pack(anchor="w")
        self.api_entry = ctk.CTkEntry(section, width=380, show="*",
                                      placeholder_text="sk-ant-api...")
        self.api_entry.pack(fill="x", pady=(0, 4))
        self.api_entry.insert(0, self.config.get("api_key", ""))

        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row, text="모델").pack(side="left")
        self.model_var = ctk.StringVar(value=self.config.get("model", "claude-opus-4-6"))
        model_menu = ctk.CTkOptionMenu(row, variable=self.model_var,
                                        values=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"])
        model_menu.pack(side="left", padx=(8, 0))

        # ── Microphone ─────────────────────────────────────────────────────
        section2 = self._section("마이크 설정")
        ctk.CTkLabel(section2, text="마이크 선택").pack(anchor="w")
        self._mic_options = self._get_mic_options()
        self.mic_var = ctk.StringVar(value=self.config.get("mic_name", "기본 장치"))
        self.mic_menu = ctk.CTkOptionMenu(section2, variable=self.mic_var,
                                           values=list(self._mic_options.keys()))
        self.mic_menu.pack(fill="x", pady=(0, 4))

        row2 = ctk.CTkFrame(section2, fg_color="transparent")
        row2.pack(fill="x")
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
                          values=["tiny", "base", "small", "medium", "large"]).pack(side="left", padx=(8, 0))

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

        # WebSocket port
        row5 = ctk.CTkFrame(section3, fg_color="transparent")
        row5.pack(fill="x")
        ctk.CTkLabel(row5, text="WebSocket Port").pack(side="left")
        self.ws_port_entry = ctk.CTkEntry(row5, width=80)
        self.ws_port_entry.insert(0, str(self.config.get("websocket_port", 9000)))
        self.ws_port_entry.pack(side="left", padx=(8, 0))

        # ── Save button ────────────────────────────────────────────────────
        save_btn = ctk.CTkButton(self, text="저장", command=self._save,
                                  fg_color="#2ECC71", hover_color="#27AE60",
                                  font=ctk.CTkFont(size=14, weight="bold"))
        save_btn.pack(pady=16, padx=20, fill="x")

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack()

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

    def _save(self):
        try:
            mic_name = self.mic_var.get()
            mic_index = self._mic_options.get(mic_name)

            new_config = {
                "api_key": self.api_entry.get().strip(),
                "model": self.model_var.get(),
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
