"""
Moddy Uninstaller – uruchamiany z folderu instalacji.
"""
import ctypes
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

import customtkinter as ctk

APP_NAME  = "Moddy Launcher"
REG_KEY   = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Moddy"
START_LNK = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Moddy Launcher.lnk"
DESK_LNK  = Path(os.environ.get("USERPROFILE", "")) / "Desktop/Moddy Launcher.lnk"


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1)
    sys.exit(0)


class Uninstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Odinstaluj Moddy")
        self.geometry("420x280")
        self.resizable(False, False)
        self._install_dir = Path(sys.executable).parent

        ctk.CTkLabel(self, text="⛏ Odinstaluj Moddy",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#FF6B35").pack(pady=(28, 6))
        ctk.CTkLabel(self,
                     text=f"Zostanie usunięty folder:\n{self._install_dir}",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="center").pack(pady=(0, 16))

        self._bar = ctk.CTkProgressBar(self, width=340)
        self._bar.pack()
        self._bar.set(0)

        self._lbl = ctk.CTkLabel(self, text="",
                                  font=ctk.CTkFont(size=11), text_color="#888")
        self._lbl.pack(pady=8)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=12)
        self._btn_yes = ctk.CTkButton(row, text="Odinstaluj", width=140, height=38,
                                       fg_color="#CC2222", hover_color="#991111",
                                       command=self._do_uninstall)
        self._btn_yes.pack(side="left", padx=8)
        ctk.CTkButton(row, text="Anuluj", width=100, height=38,
                      fg_color="#2a2a2a", hover_color="#555",
                      command=self.destroy).pack(side="left", padx=8)

    def _set(self, progress: float, text: str):
        self._bar.set(progress)
        self._lbl.configure(text=text)
        self.update()

    def _do_uninstall(self):
        self._btn_yes.configure(state="disabled")
        install_dir = self._install_dir

        self._set(0.1, "Usuwanie skrótów…")
        for lnk in (START_LNK, DESK_LNK):
            try:
                lnk.unlink(missing_ok=True)
            except Exception:
                pass

        self._set(0.3, "Usuwanie wpisów rejestru…")
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, REG_KEY)
        except Exception:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        except Exception:
            pass

        self._set(0.5, "Usuwanie plików…")

        # Usuń katalog instalacji po chwili (po zakończeniu tego procesu)
        bat = install_dir / "_uninstall_cleanup.bat"
        bat.write_text(
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'rd /s /q "{install_dir}"\n',
            encoding="utf-8"
        )
        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )

        self._set(1.0, "Odinstalowano!")
        self._lbl.configure(text_color="#4CAF50")
        self.after(1500, self.destroy)


def main():
    if not _is_admin():
        _elevate()
    app = Uninstaller()
    app.mainloop()


if __name__ == "__main__":
    main()
