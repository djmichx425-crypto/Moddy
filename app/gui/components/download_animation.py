"""
Animacja pobierania moda – Pixel Orbs.

Stany:
  idle     – ikona z subtelnym pulsującym pierścieniem
  loading  – kolorowe kwadratowe orby krążą wokół ikony;
             liczba widocznych orbów = postęp (0 → 8)
  done     – orby zwijają się do środka, błysk, zielone ✓
  error    – krótki błysk czerwony, ✗
"""
import math
import random
import tkinter as tk
import customtkinter as ctk


class DownloadAnimation(tk.Canvas):

    SIZE       = 80
    MAX_ORBS   = 8
    ORB_R      = 32    # promień orbity
    ORB_SIZE   = 7     # bok kwadratu orbu
    TRAIL_LEN  = 3     # ile śladów za orbem
    FPS        = 40    # ms/klatkę

    # kolory orbów (Minecraft-owe)
    ORB_COLORS = [
        "#4CAF50",   # trawa
        "#FF6B35",   # lawa
        "#2196F3",   # woda
        "#FFD700",   # złoto
        "#9C27B0",   # ametyst
        "#00BCD4",   # diament
        "#F44336",   # czerwień
        "#8BC34A",   # liście
    ]

    # ── init ─────────────────────────────────────────────────────────────────

    def __init__(self, parent, icon_image=None, **kwargs):
        bg = self._resolve_bg(parent)
        super().__init__(
            parent, width=self.SIZE, height=self.SIZE,
            bg=bg, highlightthickness=0, **kwargs)
        self._bg = bg
        self._icon = icon_image
        self._progress = 0.0
        self._state = "idle"
        self._angle = 0.0            # bieżący kąt bazowy orbów
        self._trails: list[list[tuple]] = [[] for _ in range(self.MAX_ORBS)]
        self._collapse_r = float(self.ORB_R)   # promień przy zwijaniu
        self._flash_frames = 0
        self._anim_id: str | None = None
        self._idle_pulse = 0.0
        self._draw_idle()

    # ── public API ────────────────────────────────────────────────────────────

    def set_icon(self, image):
        self._icon = image
        if self._state == "idle" and self._alive():
            self._draw_idle()

    def start(self):
        """Rozpocznij animację pobierania."""
        if self._anim_id:
            self.after_cancel(self._anim_id)
        self._progress = 0.0
        self._angle = 0.0
        self._trails = [[] for _ in range(self.MAX_ORBS)]
        self._state = "loading"
        self._tick()

    def set_progress(self, value: float):
        """Ustaw postęp 0.0–1.0."""
        self._progress = max(0.0, min(1.0, value))

    def finish(self):
        """Pobieranie zakończone — uruchom animację zakończenia."""
        self._progress = 1.0
        self._collapse_r = float(self.ORB_R)
        self._state = "collapsing"

    def error(self):
        """Błąd pobierania."""
        self._state = "error"
        self._flash_frames = 8

    def reset(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._state = "idle"
        self._progress = 0.0
        self._trails = [[] for _ in range(self.MAX_ORBS)]
        self._draw_idle()

    # ── master tick ───────────────────────────────────────────────────────────

    def _tick(self):
        if not self._alive():
            return
        if self._state == "loading":
            self._frame_loading()
        elif self._state == "collapsing":
            self._frame_collapsing()
        elif self._state == "error":
            self._frame_error()
        elif self._state == "idle":
            self._frame_idle()
            self._anim_id = self.after(self.FPS, self._tick)
            return
        else:
            return
        self._anim_id = self.after(self.FPS, self._tick)

    # ── idle – pulsujący pierścień ────────────────────────────────────────────

    def _draw_idle(self):
        if not self._alive():
            return
        self.delete("all")
        cx = cy = self.SIZE // 2
        self._draw_icon(cx, cy)

    def _frame_idle(self):
        """Subtelnie pulsujący obwód."""
        if not self._alive():
            return
        self._idle_pulse = (self._idle_pulse + 0.07) % (2 * math.pi)
        alpha = 0.25 + 0.25 * math.sin(self._idle_pulse)   # 0.0–0.5
        color = _lerp_color("#2a2a2a", "#FF6B35", alpha)
        self.delete("all")
        cx = cy = self.SIZE // 2
        self._draw_icon(cx, cy)
        r = 36
        # narysuj cienki pierścień
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         outline=color, width=2, fill="")

    # ── loading – orby krążą ──────────────────────────────────────────────────

    def _frame_loading(self):
        if not self._alive():
            return
        self.delete("all")
        cx = cy = self.SIZE // 2

        # ile orbów widocznych
        n = max(1, round(self._progress * self.MAX_ORBS))

        # aktualizuj ślady
        for i in range(n):
            phase = self._angle + i * (2 * math.pi / self.MAX_ORBS)
            x = cx + self.ORB_R * math.cos(phase)
            y = cy + self.ORB_R * math.sin(phase)
            trail = self._trails[i]
            trail.append((x, y))
            if len(trail) > self.TRAIL_LEN:
                trail.pop(0)

        # narysuj ślady (stopniowo zanikające)
        for i in range(n):
            color = self.ORB_COLORS[i]
            trail = self._trails[i]
            for j, (tx, ty) in enumerate(trail):
                fade = (j + 1) / (len(trail) + 1)
                c = _lerp_color(self._bg, color, fade * 0.45)
                hs = max(2, int(self.ORB_SIZE * fade * 0.6))
                self.create_rectangle(
                    tx - hs, ty - hs, tx + hs, ty + hs,
                    fill=c, outline="")

        self._draw_icon(cx, cy)

        # narysuj orby
        for i in range(n):
            phase = self._angle + i * (2 * math.pi / self.MAX_ORBS)
            x = cx + self.ORB_R * math.cos(phase)
            y = cy + self.ORB_R * math.sin(phase)
            hs = self.ORB_SIZE // 2
            color = self.ORB_COLORS[i]
            # błyszcząca obwódka
            self.create_rectangle(
                x - hs - 1, y - hs - 1, x + hs + 1, y + hs + 1,
                fill=_lerp_color(color, "#ffffff", 0.25), outline="")
            self.create_rectangle(
                x - hs, y - hs, x + hs, y + hs,
                fill=color, outline="")

        # postęp % pod ikoną
        pct = int(self._progress * 100)
        self.create_text(cx, cy + 30,
                         text=f"{pct}%",
                         fill="#888", font=("Consolas", 8))

        self._angle += 0.10   # prędkość obrotu

    # ── collapsing – zwijanie do środka ──────────────────────────────────────

    def _frame_collapsing(self):
        if not self._alive():
            return
        self.delete("all")
        cx = cy = self.SIZE // 2

        self._collapse_r *= 0.82   # spirala do środka

        if self._collapse_r < 4:
            # koniec zwijania → błysk + ✓
            self._state = "flash"
            self._flash_frames = 6
            return

        for i in range(self.MAX_ORBS):
            phase = self._angle + i * (2 * math.pi / self.MAX_ORBS)
            x = cx + self._collapse_r * math.cos(phase)
            y = cy + self._collapse_r * math.sin(phase)
            hs = max(2, int(self.ORB_SIZE * (self._collapse_r / self.ORB_R)))
            color = self.ORB_COLORS[i]
            self.create_rectangle(
                x - hs, y - hs, x + hs, y + hs,
                fill=color, outline="")

        self._draw_icon(cx, cy)
        self._angle += 0.20   # szybciej przy zwijaniu

    # ── flash + done ──────────────────────────────────────────────────────────

    def _frame_error(self):
        if not self._alive():
            return
        self.delete("all")
        cx = cy = self.SIZE // 2
        if self._flash_frames > 0:
            self.create_rectangle(0, 0, self.SIZE, self.SIZE,
                                  fill="#FF2222", outline="")
            self._flash_frames -= 1
            return
        # ✗
        self._draw_icon(cx, cy)
        self.create_oval(cx - 28, cy - 28, cx + 28, cy + 28,
                         outline="#FF4444", width=3, fill="")
        self.create_text(cx, cy + 32, text="✗",
                         fill="#FF4444", font=("Arial", 9, "bold"))
        self._state = "idle_err"   # zatrzymaj animację

    def _tick(self):  # noqa: F811 (redefinition)
        if not self._alive():
            return

        if self._state == "loading":
            self._frame_loading()
        elif self._state == "collapsing":
            self._frame_collapsing()
        elif self._state == "flash":
            self._draw_flash()
        elif self._state == "error":
            self._frame_error()
        elif self._state in ("idle", "idle_err"):
            if self._state == "idle":
                self._frame_idle()
            return   # idle nie rejestruje kolejnego tick'a z _anim_id
        else:
            return

        self._anim_id = self.after(self.FPS, self._tick)

    def _draw_flash(self):
        if not self._alive():
            return
        cx = cy = self.SIZE // 2
        self.delete("all")
        if self._flash_frames > 3:
            # jasny błysk
            self.create_rectangle(0, 0, self.SIZE, self.SIZE,
                                  fill="#AAFFAA", outline="")
        else:
            # ikona z zielonym pierścieniem i ✓
            self._draw_icon(cx, cy)
            self.create_oval(cx - 34, cy - 34, cx + 34, cy + 34,
                             outline="#4CAF50", width=3, fill="")
            self.create_text(cx, cy + 38, text="✓",
                             fill="#4CAF50",
                             font=("Arial", 10, "bold"))
        self._flash_frames -= 1
        if self._flash_frames <= 0:
            self._state = "done_hold"
            # zatrzymaj – zachowaj ostatni obraz
            self.after(1800, self.reset)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _draw_icon(self, cx: int, cy: int):
        if self._icon:
            self.create_image(cx, cy, image=self._icon, anchor="center")
        else:
            self.create_rectangle(cx - 22, cy - 22, cx + 22, cy + 22,
                                  fill="#3a3a3a", outline="#555", width=1)

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    @staticmethod
    def _resolve_bg(widget) -> str:
        try:
            fg = widget.cget("fg_color")
            if isinstance(fg, (list, tuple)):
                return fg[0] if ctk.get_appearance_mode() == "Light" else fg[1]
            return fg
        except Exception:
            try:
                return widget.cget("bg")
            except Exception:
                return "#2b2b2b"


# ── colour lerp ───────────────────────────────────────────────────────────────

def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Interpolacja liniowa między dwoma kolorami hex."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return 42, 42, 42
