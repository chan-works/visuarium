import sys
import os
import json

# Ensure project root is on path when run as PyInstaller bundle or directly
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")


def load_config() -> dict:
    defaults = {
        "api_key": "",
        "model": "claude-opus-4-6",
        "mic_index": None,
        "mic_name": "",
        "osc_ip": "127.0.0.1",
        "osc_port": 9001,
        "osc_address": "/visuarium/prompt",
        "websocket_port": 9000,
        "whisper_model": "base",
        "vad_threshold": 0.01,
        "silence_duration": 1.5,
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def main():
    # Init database
    from src.core.database import init_db
    init_db()

    config = load_config()

    from src.gui.main_window import MainWindow
    app = MainWindow(config)
    app.mainloop()


if __name__ == "__main__":
    main()
