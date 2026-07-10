"""
Moddy splash screen – wyświetlany podczas startu.
Estetyka inspirowana Opera GX: ciemny, neonowy, animowany.
"""
import math
import tkinter as tk
import customtkinter as ctk


class SplashScreen(ctk.CTkToplevel):
    W, H = 480, 270

    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.configure(fg_color="#0d0d0d")

        # Wyśrodkuj na ekranie
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.W) // 2
        y  = (sh - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self._progress  = 0.0
        self._t         = 0.0
        self._closing   = False
        self._alpha     = 255
        self._fade_after: str | None = None

        self._build()
        self.after(16, self._tick)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        c = tk.Canvas(self, width=self.W, height=self.H,
                      bg="#0d0d0d", highlightthickness=0)
        c.pack(fill="both", expand=True)
        self._c = c

        # Scanlines
        for y in range(0, self.H, 3):
            c.create_line(0, y, self.W, y, fill="#111111", width=1)

        # Narożne akcenty (Opera GX style)
        acc = "#FF6B35"
        w = 24
        for x1, y1, x2, y2 in [
            (0, 0, w, 0), (0, 0, 0, w),
            (self.W, 0, self.W - w, 0), (self.W, 0, self.W, w),
            (0, self.H, w, self.H), (0, self.H, 0, self.H - w),
            (self.W, self.H, self.W - w, self.H), (self.W, self.H, self.W, self.H - w),
        ]:
            c.create_line(x1, y1, x2, y2, fill=acc, width=2)

        # Pozioma linia ozdobna
        c.create_line(40, 155, self.W - 40, 155, fill="#1a1a1a", width=1)

        # Logo
        self._id_logo = c.create_text(
            self.W // 2, 88,
            text="⛏  moddy",
            font=("Segoe UI", 34, "bold"),
            fill="#FF6B35")

        # Podtytuł
        c.create_text(
            self.W // 2, 124,
            text="M I N E C R A F T   L A U N C H E R",
            font=("Consolas", 9),
            fill="#2a2a2a")

        # Tło paska postępu
        bx1, by, bx2, bh = 40, 185, self.W - 40, 3
        c.create_rectangle(bx1, by, bx2, by + bh, fill="#1c1c1c", outline="")
        self._bar_x1  = bx1
        self._bar_x2  = bx2
        self._bar_y1  = by
        self._bar_y2  = by + bh

        # Wypełnienie paska (aktywne)
        self._id_bar = c.create_rectangle(bx1, by, bx1, by + bh,
                                           fill="#FF6B35", outline="")
        # Poświata na końcu paska
        self._id_glow = c.create_rectangle(bx1, by - 3, bx1, by + bh + 3,
                                            fill="#ff9966", outline="",
                                            stipple="gray25")

        # Tekst statusu
        self._id_status = c.create_text(
            self.W // 2, 204,
            text="Inicjalizacja…",
            font=("Consolas", 9),
            fill="#3a3a3a")

        # Wersja
        c.create_text(self.W - 8, self.H - 8,
                      text="v1.0",
                      font=("Consolas", 7),
                      fill="#1e1e1e",
                      anchor="se")

    # ── public API ────────────────────────────────────────────────────────────

    def set_status(self, text: str):
        try:
            self._c.itemconfigure(self._id_status, text=text, fill="#3a3a3a")
        except Exception:
            pass

    def set_progress(self, value: float):
        self._progress = max(0.0, min(1.0, value))

    def close(self):
        if self._closing:
            return
        self._closing = True
        self._do_fade(255)

    # ── animation ─────────────────────────────────────────────────────────────

    def _tick(self):
        if self._closing or not self.winfo_exists():
            return
        self._t += 0.06

        # Pasek postępu
        x1 = self._bar_x1
        fill_x = x1 + (self._bar_x2 - x1) * self._progress
        self._c.coords(self._id_bar,  x1, self._bar_y1, fill_x, self._bar_y2)
        self._c.coords(self._id_glow,
                       max(x1, fill_x - 16), self._bar_y1 - 3,
                       fill_x + 4, self._bar_y2 + 3)

        # Pulsujące logo (subtelne)
        val = int(255 * (0.92 + 0.08 * math.sin(self._t * 2)))
        g   = int(107 * (0.85 + 0.15 * math.sin(self._t * 1.3)))
        b   = int(53  * (0.80 + 0.20 * math.sin(self._t * 0.9)))
        self._c.itemconfigure(self._id_logo, fill=f"#{val:02x}{g:02x}{b:02x}")

        self.after(16, self._tick)

    def _do_fade(self, alpha: int):
        if not self.winfo_exists():
            return
        if alpha <= 0:
            try:
                self.destroy()
            except Exception:
                pass
            return
        try:
            self.attributes("-alpha", alpha / 255)
        except Exception:
            pass
        self.after(18, lambda: self._do_fade(alpha - 45))
