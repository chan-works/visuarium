import customtkinter as ctk
from src.gui.session_panel import SessionPanel
from src.gui.settings_panel import SettingsPanel
from src.gui.data_panel import DataPanel
from src.core.websocket_server import WebSocketServer
from src.core.osc_sender import OSCSender


class MainWindow(ctk.CTk):
    def __init__(self, config: dict):
        super().__init__()
        self.config_data = config
        self.title("Visuarium — AI Media Art Installation")
        self.geometry("1000x720")
        self.minsize(900, 650)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── Background services ────────────────────────────────────────────
        self.ws_server = WebSocketServer(port=config.get("websocket_port", 9000))
        self.ws_server.start()

        self.osc_sender = OSCSender(
            ip=config.get("osc_ip", "127.0.0.1"),
            port=config.get("osc_port", 9001),
            address=config.get("osc_address", "/visuarium/prompt"),
        )

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        # ── Sidebar ────────────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self, width=160, corner_radius=0, fg_color="#151515")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo = ctk.CTkLabel(sidebar, text="VISUARIUM",
                             font=ctk.CTkFont(size=16, weight="bold"),
                             text_color="#A0C4E4")
        logo.pack(pady=(24, 32))

        self._nav_buttons = {}
        tabs = [("🎤  세션", "session"), ("⚙  설정", "settings"), ("📊  데이터", "data")]
        for label, key in tabs:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                fg_color="transparent", hover_color="#2C2C2C",
                font=ctk.CTkFont(size=13), corner_radius=6,
                command=lambda k=key: self._show_tab(k)
            )
            btn.pack(fill="x", padx=10, pady=3)
            self._nav_buttons[key] = btn

        ws_label = ctk.CTkLabel(sidebar, text="WS :9000\nOSC :9001",
                                 font=ctk.CTkFont(size=10), text_color="#555",
                                 justify="left")
        ws_label.pack(side="bottom", pady=16, padx=10, anchor="w")

        # ── Main content area ──────────────────────────────────────────────
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="#1A1A1A")
        self.content.pack(side="right", fill="both", expand=True)

        self.session_panel = SessionPanel(
            self.content, config=self.config_data,
            on_prompt_ready=self._on_prompt_ready,
        )
        self.settings_panel = SettingsPanel(
            self.content, config=self.config_data,
            on_save=self._on_config_save,
        )
        self.data_panel = DataPanel(self.content)

        self._current_tab = None
        self._show_tab("session")

    def _show_tab(self, key: str):
        if self._current_tab == key:
            return
        for panel in (self.session_panel, self.settings_panel, self.data_panel):
            panel.pack_forget()
        map_ = {
            "session": self.session_panel,
            "settings": self.settings_panel,
            "data": self.data_panel,
        }
        map_[key].pack(fill="both", expand=True)
        if key == "data":
            self.data_panel.refresh()
        self._current_tab = key
        # Highlight active nav button
        for k, btn in self._nav_buttons.items():
            btn.configure(fg_color="#2C5F8A" if k == key else "transparent")

    def _on_prompt_ready(self, prompt: str):
        self.ws_server.send_prompt(prompt)
        self.osc_sender.send_prompt(prompt)

    def _on_config_save(self, new_config: dict):
        self.config_data.update(new_config)
        # Update WebSocket port if changed
        # (restart would require user to restart app — keep simple)
        self.osc_sender.update(
            ip=new_config.get("osc_ip", "127.0.0.1"),
            port=new_config.get("osc_port", 9001),
            address=new_config.get("osc_address", "/visuarium/prompt"),
        )
        self.session_panel.update_config(new_config)

    def _on_close(self):
        self.ws_server.stop()
        self.destroy()
