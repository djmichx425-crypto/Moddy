"""
Menedżer wydajności — FPS, RAM, CPU, GPU, temperatury.
Wykresy historyczne. Porównanie sesji.
"""
import tkinter as tk
import customtkinter as ctk
import math
import threading

from ...core.session_stats import SessionStatsCollector, FrameStats
from ...core.play_time_tracker import get_recent_sessions


class _SparkCanvas(tk.Canvas):
    """Mini wykres liniowy (sparkline)."""

    def __init__(self, parent, width=260, height=60,
                 color="#FF6B35", label="", max_val=100, **kw):
        bg = "#111"
        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0, **kw)
        self._color   = color
        self._label   = label
        self._max_val = max_val
        self._data: list[float] = []
        self._w = width
        self._h = height

    def update_data(self, data: list[float], max_val: float | None = None):
        self._data = list(data)
        if max_val:
            self._max_val = max_val
        self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = self._w, self._h
        data  = self._data
        if not data:
            self.create_text(w // 2, h // 2, text="Brak danych",
                             fill="#444", font=("Consolas", 9))
            return

        mx = max(max(data), self._max_val, 1)
        n  = len(data)
        pts = []
        for i, v in enumerate(data):
            x = int(i / max(n - 1, 1) * (w - 4)) + 2
            y = h - 4 - int(v / mx * (h - 8))
            pts.append((x, y))

        # Area fill
        poly = [(2, h - 2)] + pts + [(pts[-1][0], h - 2)]
        flat = [c for p in poly for c in p]
        self.create_polygon(flat, fill=self._color + "33", outline="")

        # Line
        for i in range(len(pts) - 1):
            self.create_line(pts[i][0], pts[i][1],
                             pts[i+1][0], pts[i+1][1],
                             fill=self._color, width=2)

        # Current value
        cur = data[-1]
        self.create_text(w - 4, 8, text=f"{cur:.0f}",
                         fill=self._color, font=("Consolas", 9), anchor="ne")
        if self._label:
            self.create_text(4, 8, text=self._label,
                             fill="#666", font=("Consolas", 8), anchor="nw")


class PerformancePage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 stats_collector: SessionStatsCollector | None = None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._collector = stats_collector or SessionStatsCollector()
        self._running   = False
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="📊  Menedżer wydajności",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        self._toggle_btn = ctk.CTkButton(
            top, text="▶ Start", width=90, height=30,
            fg_color="#4CAF50", hover_color="#388E3C",
            command=self._toggle)
        self._toggle_btn.pack(side="right", padx=16, pady=12)

        tab = ctk.CTkTabview(self, corner_radius=8)
        tab.pack(fill="both", expand=True, padx=16, pady=10)
        tab.add("📈  Na żywo")
        tab.add("📋  Historia sesji")

        self._build_live(tab.tab("📈  Na żywo"))
        self._build_history(tab.tab("📋  Historia sesji"))

    # ── live tab ──────────────────────────────────────────────────────────────

    def _build_live(self, parent):
        # Górny rząd: duże liczby
        nums = ctk.CTkFrame(parent, fg_color="transparent")
        nums.pack(fill="x", pady=(8, 4))

        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        metrics = [
            ("FPS",  "fps",  "#FFD700"),
            ("CPU",  "cpu",  "#FF6B35"),
            ("RAM",  "ram",  "#2196F3"),
            ("GPU",  "gpu",  "#9C27B0"),
            ("°GPU", "temp", "#F44336"),
        ]
        for label, key, color in metrics:
            box = ctk.CTkFrame(nums, corner_radius=10)
            box.pack(side="left", expand=True, fill="x",
                     padx=(0, 4), pady=0)
            ctk.CTkLabel(box, text=label,
                         font=ctk.CTkFont(size=10), text_color="#666").pack(pady=(8, 0))
            lbl = ctk.CTkLabel(box, text="–",
                               font=ctk.CTkFont(size=20, weight="bold"),
                               text_color=color)
            lbl.pack(pady=(0, 8))
            self._stat_labels[key] = lbl

        # Wykresy
        charts = ctk.CTkFrame(parent, fg_color="transparent")
        charts.pack(fill="both", expand=True)
        charts.columnconfigure((0, 1), weight=1)

        self._charts: dict[str, _SparkCanvas] = {}
        chart_defs = [
            ("fps",  "FPS",        "#FFD700", 0, 0, 300),
            ("cpu",  "CPU %",      "#FF6B35", 0, 1, 100),
            ("ram",  "RAM MB",     "#2196F3", 1, 0, 16000),
            ("gpu",  "GPU %",      "#9C27B0", 1, 1, 100),
        ]
        for key, lbl, color, r, c, mx in chart_defs:
            frame = ctk.CTkFrame(charts, corner_radius=8, fg_color="#111")
            frame.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(frame, text=lbl,
                         font=ctk.CTkFont(size=10), text_color="#555").pack(
                anchor="w", padx=8, pady=(6, 2))
            sc = _SparkCanvas(frame, width=280, height=70,
                              color=color, max_val=mx)
            sc.pack(padx=8, pady=(0, 8))
            self._charts[key] = sc

        # Alert
        self._alert = ctk.CTkLabel(parent, text="",
                                    font=ctk.CTkFont(size=11),
                                    text_color="#FF8C00")
        self._alert.pack()

    # ── history tab ───────────────────────────────────────────────────────────

    def _build_history(self, parent):
        self._hist_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent")
        self._hist_scroll.pack(fill="both", expand=True)
        self._hist_scroll.columnconfigure(0, weight=1)
        self._refresh_history()

    def _refresh_history(self):
        for w in self._hist_scroll.winfo_children():
            w.destroy()

        sessions = get_recent_sessions(20)
        if not sessions:
            ctk.CTkLabel(self._hist_scroll,
                         text="Brak historii sesji.\nUruchom grę aby rejestrować statystyki.",
                         font=ctk.CTkFont(size=12), text_color="#555",
                         justify="center").pack(pady=40)
            return

        # Nagłówek
        hdr = ctk.CTkFrame(self._hist_scroll, fg_color="#1e1e1e", corner_radius=6)
        hdr.pack(fill="x", pady=(0, 4))
        for txt, w in [("Data", 90), ("Instalacja", 150), ("Czas", 60),
                        ("Avg FPS", 70), ("Avg CPU", 70), ("Avg RAM", 80)]:
            ctk.CTkLabel(hdr, text=txt, width=w,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#888").pack(side="left", padx=6, pady=6)

        for sess in sessions:
            self._make_session_row(sess)

        # Porównanie (top 3)
        self._make_comparison(sessions[:5])

    def _make_session_row(self, s: dict):
        row = ctk.CTkFrame(self._hist_scroll, corner_radius=6, height=36)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        dur = self._fmt(s.get("duration_s", 0))
        for txt, w in [
            (s.get("start", "")[:10],          90),
            (s.get("installation", "")[:18],   150),
            (dur,                               60),
            (f"{s.get('avg_fps', 0):.0f}",     70),
            (f"{s.get('avg_cpu', 0):.0f}%",    70),
            (f"{s.get('avg_ram_mb', 0):.0f}M", 80),
        ]:
            ctk.CTkLabel(row, text=txt, width=w,
                         font=ctk.CTkFont(size=10), text_color="#bbb",
                         anchor="w").pack(side="left", padx=6)

    def _make_comparison(self, sessions: list[dict]):
        if len(sessions) < 2:
            return
        ctk.CTkLabel(self._hist_scroll,
                     text="PORÓWNANIE SESJI",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(anchor="w", pady=(14, 4))

        frame = ctk.CTkFrame(self._hist_scroll, corner_radius=8, fg_color="#111")
        frame.pack(fill="x", pady=(0, 8))

        metrics = [("avg_fps", "FPS", "#FFD700", 300),
                   ("avg_cpu", "CPU%", "#FF6B35", 100),
                   ("avg_ram_mb", "RAM", "#2196F3", 16000)]
        for key, label, color, mx in metrics:
            vals = [s.get(key, 0) for s in sessions]
            if not any(vals):
                continue
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)
            ctk.CTkLabel(row, text=label, width=44,
                         font=ctk.CTkFont(size=10), text_color="#666").pack(side="left")
            sc = _SparkCanvas(row, width=300, height=28, color=color, max_val=mx)
            sc.update_data(vals)
            sc.pack(side="left")
            best = max(vals) if key == "avg_fps" else min(v for v in vals if v > 0)
            ctk.CTkLabel(row, text=f"best: {best:.0f}",
                         font=ctk.CTkFont(size=9), text_color=color).pack(side="left", padx=6)

    # ── controls ──────────────────────────────────────────────────────────────

    def _toggle(self):
        if not self._running:
            self._running = True
            self._toggle_btn.configure(text="⏹ Stop",
                                        fg_color="#aa2222", hover_color="#881111")
            self._collector.set_callback(self._on_stats)
            self._collector.start()
        else:
            self._running = False
            self._toggle_btn.configure(text="▶ Start",
                                        fg_color="#4CAF50", hover_color="#388E3C")
            self._collector.stop()

    def _on_stats(self, s: FrameStats):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        def _ui():
            try:
                if not self.winfo_exists():
                    return
                fps_txt  = f"{s.fps:.0f}" if s.fps > 0 else "–"
                self._stat_labels["fps"].configure(text=fps_txt)
                self._stat_labels["cpu"].configure(text=f"{s.cpu:.0f}%")
                self._stat_labels["ram"].configure(text=f"{s.ram_mb:.0f}")
                self._stat_labels["gpu"].configure(
                    text=f"{s.gpu_usage:.0f}%" if s.gpu_usage else "–")
                self._stat_labels["temp"].configure(
                    text=f"{s.gpu_temp:.0f}°" if s.gpu_temp else "–")

                hist = self._collector.get_history()
                for key, data in hist.items():
                    if key in self._charts:
                        self._charts[key].update_data(data)
            except Exception:
                pass

        self.after(0, _ui)

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._refresh_history()

    @staticmethod
    def _fmt(secs: int) -> str:
        if secs < 60:    return f"{secs}s"
        if secs < 3600:  return f"{secs//60}m"
        return f"{secs//3600}h{(secs%3600)//60}m"
