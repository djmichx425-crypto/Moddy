"""
Strona uruchamiania gry / postępu instalacji.
Pokazuje logi, pasek postępu i status w czasie rzeczywistym.
"""
import customtkinter as ctk
import threading

from ...core import minecraft_launcher as launcher
from ...core.accounts_manager import get_selected_account


class PlayPage(ctk.CTkFrame):
    """Wyświetla postęp instalacji lub konsole gry podczas uruchamiania."""

    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._installation: dict | None = None
        self._mode = "idle"   # "installing" | "running" | "done" | "error"
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # nagłówek
        top = ctk.CTkFrame(self, fg_color="#222222", corner_radius=0)
        top.pack(fill="x")
        self._title_lbl = ctk.CTkLabel(
            top, text="Uruchamianie…",
            font=ctk.CTkFont(size=18, weight="bold"))
        self._title_lbl.pack(side="left", padx=20, pady=14)

        self._back_btn = ctk.CTkButton(
            top, text="← Wstecz", width=90, height=30,
            fg_color="#3a3a3a", hover_color="#555",
            command=lambda: self._navigate("home"))
        self._back_btn.pack(side="right", padx=16, pady=10)

        # status + pasek
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="x", padx=24, pady=(16, 8))

        self._status_lbl = ctk.CTkLabel(
            mid, text="Przygotowywanie…",
            font=ctk.CTkFont(size=13), text_color="#aaa", anchor="w")
        self._status_lbl.pack(fill="x")

        self._progress = ctk.CTkProgressBar(mid, height=10, corner_radius=5)
        self._progress.pack(fill="x", pady=(6, 0))
        self._progress.set(0)

        self._progress_lbl = ctk.CTkLabel(
            mid, text="", font=ctk.CTkFont(size=10), text_color="#555", anchor="w")
        self._progress_lbl.pack(fill="x")

        # konsola logów
        log_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#111")
        log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        self._log = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#111", text_color="#ccc", corner_radius=0,
            wrap="word", state="disabled")
        self._log.pack(fill="both", expand=True, padx=4, pady=4)

        # przyciski dół
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=24, pady=(0, 16))

        self._stop_btn = ctk.CTkButton(
            bottom, text="⏹  Zatrzymaj grę", width=160, height=36,
            fg_color="#aa2222", hover_color="#881111",
            state="disabled",
            command=self._stop)
        self._stop_btn.pack(side="left")

        self._clear_btn = ctk.CTkButton(
            bottom, text="Wyczyść logi", width=120, height=36,
            fg_color="#3a3a3a", hover_color="#555",
            command=self._clear_log)
        self._clear_btn.pack(side="left", padx=8)

        self._play_again_btn = ctk.CTkButton(
            bottom, text="▶  Graj ponownie", width=160, height=36,
            fg_color="#4CAF50", hover_color="#388E3C",
            state="disabled",
            command=self._play_again)
        self._play_again_btn.pack(side="right")

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, installation: dict | None = None,
                mode: str = "launch", **_):
        """
        mode = "install"  – instaluj, potem wróć do home
        mode = "launch"   – uruchom grę
        mode = "install_and_launch" – najpierw instaluj, potem uruchom
        """
        self._installation = installation or {}
        self._clear_log()
        self._progress.set(0)
        self._progress_lbl.configure(text="")
        self._stop_btn.configure(state="disabled")
        self._play_again_btn.configure(state="disabled")
        self._back_btn.configure(state="normal")

        name = self._installation.get("name", "Minecraft")
        loader = self._installation.get("loader", "vanilla").capitalize()
        ver = self._installation.get("version", "")
        self._title_lbl.configure(text=f"{name}  ·  {loader} {ver}")

        if mode == "install":
            self._start_install(then_launch=False)
        elif mode == "install_and_launch":
            self._start_install(then_launch=True)
        else:
            self._start_launch()

    # ── install ───────────────────────────────────────────────────────────────

    def _start_install(self, then_launch: bool = False):
        self._mode = "installing"
        self._status_lbl.configure(text="Instalowanie…", text_color="#aaa")
        self._back_btn.configure(state="disabled")
        self._max_val = 1

        def set_status(s: str):
            self.after(0, lambda m=s: self._status_lbl.configure(text=m))
            self.after(0, lambda m=s: self._log_append(f"[INFO] {m}"))

        def set_max(m: int):
            self._max_val = max(m, 1)
            self.after(0, lambda: self._progress_lbl.configure(
                text=f"0 / {self._max_val}"))

        def set_progress(p: int):
            frac = min(p / self._max_val, 1.0)
            self.after(0, lambda: self._progress.set(frac))
            self.after(0, lambda: self._progress_lbl.configure(
                text=f"{p} / {self._max_val}"))

        cb = {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}

        def _worker():
            try:
                launcher.install_version(self._installation, callback=cb)
                self.after(0, lambda: self._on_install_done(then_launch))
            except Exception as e:
                err = str(e)
                self.after(0, lambda m=err: self._on_error(m))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_install_done(self, then_launch: bool):
        self._progress.set(1.0)
        self._status_lbl.configure(text="✓ Instalacja zakończona!", text_color="#4CAF50")
        self._log_append("\n✓ Instalacja zakończona pomyślnie.")
        self._back_btn.configure(state="normal")
        # Oznacz jako zainstalowane
        self._installation["installed"] = True
        if then_launch:
            self.after(800, self._start_launch)
        else:
            self._mode = "done"
            self._play_again_btn.configure(state="normal")

    # ── launch ────────────────────────────────────────────────────────────────

    def _start_launch(self):
        account = get_selected_account()
        if not account:
            self._on_error(
                "Brak konta!\nDodaj konto w zakładce 'Konta' przed uruchomieniem gry.")
            return

        self._mode = "running"
        self._status_lbl.configure(
            text=f"Uruchamianie jako {account['username']}…", text_color="#aaa")
        self._progress.set(0)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._stop_btn.configure(state="normal")
        self._back_btn.configure(state="disabled")
        self._log_append(f"[LAUNCHER] Uruchamianie {self._installation.get('name')}…")
        self._log_append(f"[LAUNCHER] Konto: {account['username']} ({account['type']})")

        try:
            launcher.launch(
                self._installation,
                account,
                on_start=self._on_game_start,
                on_stop=self._on_game_stop,
                on_output=self._on_game_output,
            )
        except RuntimeError as e:
            err = str(e)
            self.after(0, lambda m=err: self._on_error(m))

    def _on_game_start(self):
        self.after(0, lambda: self._status_lbl.configure(
            text="🎮  Gra uruchomiona!", text_color="#4CAF50"))
        self.after(0, lambda: self._log_append("[LAUNCHER] Gra uruchomiona."))

    def _on_game_stop(self):
        self.after(0, self._game_finished)

    def _on_game_output(self, line: str):
        self.after(0, lambda l=line: self._log_append(l))

    def _game_finished(self):
        self._mode = "done"
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(1.0)
        self._status_lbl.configure(text="✓ Gra zakończona", text_color="#888")
        self._stop_btn.configure(state="disabled")
        self._play_again_btn.configure(state="normal")
        self._back_btn.configure(state="normal")
        self._log_append("\n[LAUNCHER] Gra zakończona.")

    # ── error ─────────────────────────────────────────────────────────────────

    def _on_error(self, msg: str):
        self._mode = "error"
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(0)
        self._status_lbl.configure(text=f"✗ Błąd", text_color="#FF4444")
        self._log_append(f"\n[BŁĄD] {msg}")
        self._back_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _log_append(self, text: str):
        try:
            if not self.winfo_exists():
                return
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        except Exception:
            pass

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _stop(self):
        # Zatrzymanie gry nie jest trywialne – gra to osobny proces
        # Na razie informacja dla użytkownika
        self._log_append("[LAUNCHER] Aby zamknąć grę, zamknij okno Minecraft.")
        self._stop_btn.configure(state="disabled")

    def _play_again(self):
        self.on_show(installation=self._installation, mode="launch")
