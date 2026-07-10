"""
Moddy Launcher – punkt wejścia.
Serwer Moddy startuje w tle (bez blokowania GUI).
"""
import sys
import os
import threading

if getattr(sys, "frozen", False):
    BASE_DIR   = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS  # type: ignore
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)


def _start_server():
    try:
        import uvicorn
        from server.config import SERVER_HOST, SERVER_PORT
        uvicorn.run(
            "server.main:app",
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="error",
            access_log=False,
        )
    except Exception as e:
        print(f"[Serwer] Błąd: {e}")


if __name__ == "__main__":
    # Serwer startuje w tle – nie blokujemy GUI
    threading.Thread(target=_start_server, daemon=True).start()

    from app.gui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()
