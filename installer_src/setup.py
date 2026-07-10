"""
Moddy Installer – zbudowany przez PyInstaller, zawiera pliki apki w środku.
Kroki: Witaj → Licencja → Lokalizacja → Instalacja → Gotowe
"""
import ctypes
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

import customtkinter as ctk

# ── stałe ────────────────────────────────────────────────────────────────────

APP_NAME    = "Moddy Launcher"
APP_VERSION = "Beta 1.0"
APP_EXE     = "Moddy.exe"
UNINSTALLER = "uninstall.exe"
DEFAULT_DIR = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Moddy"
REG_KEY     = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Moddy"
START_MENU  = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"
DESKTOP     = Path(os.environ.get("USERPROFILE", "")) / "Desktop"

EULA = """\
UMOWA LICENCYJNA UŻYTKOWNIKA KOŃCOWEGO
Moddy Launcher – Beta 1.0
══════════════════════════════════════

Instalując lub używając oprogramowania Moddy Launcher akceptujesz
warunki niniejszej umowy.

1. LICENCJA
   Otrzymujesz niewyłączne prawo do używania Moddy Launcher
   wyłącznie na własny użytek niekomercyjny.

2. OGRANICZENIA
   Nie możesz sprzedawać, dekompilować ani modyfikować aplikacji.

3. MINECRAFT
   Moddy nie jest powiązany z Mojang Studios ani Microsoft.
   Do gry wymagana jest legalna kopia Minecraft®.

4. WERSJA BETA
   Aplikacja jest w fazie testów. Może zawierać błędy.

5. GWARANCJA
   Oprogramowanie dostarczane jest „takie jakie jest",
   bez żadnych gwarancji.

6. DANE
   Moddy nie zbiera danych osobowych bez zgody użytkownika.

Kontakt: support@moddy.app
"""


# ── UAC elevation ─────────────────────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable,
        " ".join(f'"{a}"' for a in sys.argv), None, 1)
    sys.exit(0)


# ── ścieżka do zasobów osadzonych ────────────────────────────────────────────

def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "app_files"
    return Path(__file__).parent.parent / "dist" / "Moddy"


# ── skróty ────────────────────────────────────────────────────────────────────

def _create_shortcut(target: Path, link: Path):
    ps = (
        f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{link}");'
        f'$s.TargetPath="{target}";'
        f'$s.WorkingDirectory="{target.parent}";'
        f'$s.IconLocation="{target}";'
        f'$s.Save()'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True,
    )


# ── rejestr ───────────────────────────────────────────────────────────────────

def _register(install_dir: Path):
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, REG_KEY)
    except PermissionError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    uninstall_exe = install_dir / UNINSTALLER
    pairs = [
        ("DisplayName",          APP_NAME + " " + APP_VERSION),
        ("DisplayVersion",       "1.0.0-beta"),
        ("Publisher",            "Moddy"),
        ("UninstallString",      str(uninstall_exe)),
        ("InstallLocation",      str(install_dir)),
        ("DisplayIcon",          str(install_dir / APP_EXE)),
        ("URLInfoAbout",         "https://moddy.app"),
        ("NoModify",             1),
        ("NoRepair",             1),
    ]
    for name, val in pairs:
        t = winreg.REG_DWORD if isinstance(val, int) else winreg.REG_SZ
        winreg.SetValueEx(key, name, 0, t, val)
    winreg.CloseKey(key)


# ── GUI ───────────────────────────────────────────────────────────────────────

class Installer(ctk.CTk):
    STEPS = ["Witaj", "Licencja", "Lokalizacja", "Instalacja", "Gotowe"]

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(f"Instalator {APP_NAME}")
        self.geometry("560x440")
        self.resizable(False, False)
        self._step   = 0
        self._dir    = ctk.StringVar(value=str(DEFAULT_DIR))
        self._desk   = ctk.BooleanVar(value=True)
        self._launch = ctk.BooleanVar(value=True)
        self._eula_ok = ctk.BooleanVar(value=False)
        self._build()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Nagłówek
        hdr = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color="#111")
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⛏ Moddy",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#FF6B35").pack(side="left", padx=20)
        self._step_lbl = ctk.CTkLabel(hdr, text="",
                                       font=ctk.CTkFont(size=11),
                                       text_color="#555")
        self._step_lbl.pack(side="right", padx=20)

        # Pasek kroków
        bar = ctk.CTkFrame(self, height=4, corner_radius=0, fg_color="#1e1e1e")
        bar.pack(fill="x")
        self._step_bar = ctk.CTkProgressBar(bar, height=4, corner_radius=0,
                                             progress_color="#FF6B35")
        self._step_bar.pack(fill="x")
        self._step_bar.set(0)

        # Obszar treści
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self._content.pack(fill="both", expand=True)

        # Przyciski dół
        nav = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color="#111")
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)
        self._btn_back = ctk.CTkButton(nav, text="← Wstecz", width=110, height=36,
                                        fg_color="#2a2a2a", hover_color="#444",
                                        command=self._back)
        self._btn_back.pack(side="left", padx=16, pady=10)
        self._btn_next = ctk.CTkButton(nav, text="Dalej →", width=130, height=36,
                                        fg_color="#FF6B35", hover_color="#cc4400",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        command=self._next)
        self._btn_next.pack(side="right", padx=16, pady=10)

        self._show_step(0)

    def _clear(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _show_step(self, n: int):
        self._step = n
        self._step_bar.set((n) / (len(self.STEPS) - 1))
        self._step_lbl.configure(text=f"Krok {n+1} z {len(self.STEPS)}")
        self._btn_back.configure(state="normal" if n > 0 else "disabled")
        self._btn_next.configure(
            text="Zakończ" if n == len(self.STEPS) - 1 else
            "Instaluj" if n == 2 else "Dalej →")
        self._clear()
        [self._s_welcome, self._s_license, self._s_dir,
         self._s_install, self._s_done][n]()

    def _next(self):
        if self._step == 1 and not self._eula_ok.get():
            return
        if self._step == 2:
            self._show_step(3)
            self.after(100, self._do_install)
            return
        if self._step == len(self.STEPS) - 1:
            if self._launch.get():
                d = Path(self._dir.get())
                exe = d / APP_EXE
                if exe.exists():
                    subprocess.Popen([str(exe)],
                                     creationflags=subprocess.DETACHED_PROCESS)
            self.destroy()
            return
        self._show_step(self._step + 1)

    def _back(self):
        if self._step > 0:
            self._show_step(self._step - 1)

    # ── kroki ─────────────────────────────────────────────────────────────────

    def _s_welcome(self):
        f = self._content
        ctk.CTkLabel(f, text="✨",
                     font=ctk.CTkFont(size=56)).pack(pady=(40, 8))
        ctk.CTkLabel(f, text=f"Witaj w instalatorze {APP_NAME}",
                     font=ctk.CTkFont(size=18, weight="bold")).pack()
        ctk.CTkLabel(f, text=APP_VERSION,
                     font=ctk.CTkFont(size=12),
                     text_color="#FF6B35").pack(pady=(2, 16))
        ctk.CTkLabel(f,
                     text="Nowoczesny launcher Minecraft z obsługą modów,\n"
                          "modpacków i wbudowanym AI generatorem.\n\n"
                          "Kliknij Dalej aby kontynuować.",
                     font=ctk.CTkFont(size=12), text_color="#aaa",
                     justify="center").pack()

    def _s_license(self):
        f = self._content
        ctk.CTkLabel(f, text="Umowa licencyjna",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=24, pady=(16, 8))
        box = ctk.CTkTextbox(f, height=220, font=ctk.CTkFont(family="Consolas", size=10))
        box.pack(fill="x", padx=24)
        box.insert("1.0", EULA)
        box.configure(state="disabled")
        ctk.CTkCheckBox(f, text="Przeczytałem i akceptuję warunki licencji",
                        variable=self._eula_ok,
                        font=ctk.CTkFont(size=12),
                        command=lambda: self._btn_next.configure(
                            state="normal" if self._eula_ok.get() else "disabled")
                        ).pack(anchor="w", padx=24, pady=10)
        self._btn_next.configure(
            state="normal" if self._eula_ok.get() else "disabled")

    def _s_dir(self):
        f = self._content
        ctk.CTkLabel(f, text="Lokalizacja instalacji",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=24, pady=(24, 8))
        ctk.CTkLabel(f,
                     text="Moddy zostanie zainstalowany w wybranym folderze.",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(
            anchor="w", padx=24)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=12)
        ctk.CTkEntry(row, textvariable=self._dir, height=36,
                     font=ctk.CTkFont(size=11)).pack(side="left", fill="x",
                                                      expand=True, padx=(0, 8))
        ctk.CTkButton(row, text="Przeglądaj", width=100, height=36,
                      fg_color="#2a2a2a", hover_color="#555",
                      command=self._browse).pack(side="left")

        ctk.CTkFrame(f, height=1, fg_color="#2a2a2a").pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(f, text="Opcje:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", padx=24)
        ctk.CTkCheckBox(f, text="Utwórz skrót na pulpicie",
                        variable=self._desk,
                        font=ctk.CTkFont(size=12)).pack(anchor="w", padx=24, pady=4)

    def _browse(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(initialdir=self._dir.get(),
                                    title="Wybierz folder instalacji")
        if d:
            self._dir.set(d)

    def _s_install(self):
        f = self._content
        ctk.CTkLabel(f, text="Instalowanie…",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(40, 16))
        self._prog_bar = ctk.CTkProgressBar(f, width=400)
        self._prog_bar.pack()
        self._prog_bar.set(0)
        self._prog_lbl = ctk.CTkLabel(f, text="Przygotowanie…",
                                       font=ctk.CTkFont(size=11), text_color="#888")
        self._prog_lbl.pack(pady=8)
        self._btn_next.configure(state="disabled")
        self._btn_back.configure(state="disabled")

    def _set_prog(self, val: float, text: str):
        self._prog_bar.set(val)
        self._prog_lbl.configure(text=text)
        self.update()

    def _do_install(self):
        src_dir  = _bundle_dir()
        dest_dir = Path(self._dir.get())

        try:
            self._set_prog(0.05, "Tworzenie folderu…")
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Kopiuj pliki
            files = list(src_dir.rglob("*"))
            total = len(files)
            for i, src in enumerate(files, 1):
                self._set_prog(0.05 + 0.80 * i / total,
                               f"Kopiowanie: {src.name}")
                rel  = src.relative_to(src_dir)
                dest = dest_dir / rel
                if src.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

            self._set_prog(0.88, "Tworzenie skrótów…")
            exe_path = dest_dir / APP_EXE
            START_MENU.mkdir(parents=True, exist_ok=True)
            _create_shortcut(exe_path, START_MENU / f"{APP_NAME}.lnk")
            if self._desk.get():
                _create_shortcut(exe_path, DESKTOP / f"{APP_NAME}.lnk")

            self._set_prog(0.95, "Rejestrowanie aplikacji…")
            _register(dest_dir)

            self._set_prog(1.0, "Zakończono!")
            self._prog_lbl.configure(text_color="#4CAF50")
            self.after(800, lambda: self._show_step(4))

        except Exception as e:
            self._set_prog(0, f"Błąd: {e}")
            self._prog_lbl.configure(text_color="#FF4444")
            self._btn_back.configure(state="normal")

    def _s_done(self):
        f = self._content
        ctk.CTkLabel(f, text="✅",
                     font=ctk.CTkFont(size=52)).pack(pady=(36, 8))
        ctk.CTkLabel(f, text=f"{APP_NAME} zainstalowany!",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#4CAF50").pack()
        ctk.CTkLabel(f, text=self._dir.get(),
                     font=ctk.CTkFont(size=10), text_color="#555").pack(pady=4)
        ctk.CTkCheckBox(f, text="Uruchom Moddy",
                        variable=self._launch,
                        font=ctk.CTkFont(size=12)).pack(pady=(16, 0))


# ── tryb cichej aktualizacji ──────────────────────────────────────────────────

class SilentUpdater(ctk.CTk):
    """Uruchamiany z flagą --update DIR. Kopiuje pliki bez wizarda."""

    def __init__(self, install_dir: Path):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Moddy – Aktualizacja")
        self.geometry("420x180")
        self.resizable(False, False)
        self._dir = install_dir

        ctk.CTkLabel(self, text="⛏  Moddy – Aktualizacja",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#FF6B35").pack(pady=(24, 8))

        self._bar = ctk.CTkProgressBar(self, width=360)
        self._bar.pack()
        self._bar.set(0)

        self._lbl = ctk.CTkLabel(self, text="Przygotowanie…",
                                  font=ctk.CTkFont(size=11), text_color="#888")
        self._lbl.pack(pady=8)

        self.after(200, self._run)

    def _set(self, val: float, text: str):
        self._bar.set(val)
        self._lbl.configure(text=text)
        self.update()

    def _run(self):
        src_dir  = _bundle_dir()
        dest_dir = self._dir
        try:
            files = list(src_dir.rglob("*"))
            total = len(files)
            for i, src in enumerate(files, 1):
                self._set(i / total, f"Aktualizowanie: {src.name}")
                rel  = src.relative_to(src_dir)
                dest = dest_dir / rel
                if src.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

            self._set(1.0, "✅ Zaktualizowano!")
            self._lbl.configure(text_color="#4CAF50")

            # Uruchom nową wersję Moddy
            exe = dest_dir / APP_EXE
            if exe.exists():
                subprocess.Popen([str(exe)],
                                 creationflags=subprocess.DETACHED_PROCESS)
            self.after(1500, self.destroy)

        except Exception as e:
            self._set(0, f"❌ Błąd: {e}")
            self._lbl.configure(text_color="#FF4444")


# ── entry ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--update", metavar="DIR", default=None,
                    help="Cicha aktualizacja do podanego katalogu")
    args, _ = ap.parse_known_args()

    if not _is_admin():
        _elevate()

    if args.update:
        app = SilentUpdater(Path(args.update))
    else:
        app = Installer()

    app.mainloop()


if __name__ == "__main__":
    main()
