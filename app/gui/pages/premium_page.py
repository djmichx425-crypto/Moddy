"""
Strona Premium – zaloguj się aby odblokować.
"""
import tkinter as tk
import customtkinter as ctk
import threading

from ...core.sync_manager import (
    list_snapshots, save_config_snapshot, restore_snapshot,
    delete_snapshot, sync_to_server, sync_from_server,
)
from ...core.resource_monitor import ResourceMonitor
from ...auth.token_store import load_session, is_premium


class PremiumPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 get_active_installation=None,
                 resource_monitor: ResourceMonitor | None = None,
                 get_user_info=None,
                 on_tier_change=None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate      = navigate
        self._get_inst      = get_active_installation
        self._get_user_info = get_user_info
        self._monitor       = resource_monitor or ResourceMonitor()
        self._gate          = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="✨  Moddy Premium",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color="#FFD700").pack(side="left", padx=20, pady=13)

        tab = ctk.CTkTabview(self, corner_radius=8)
        tab.pack(fill="both", expand=True, padx=16, pady=12)

        for t in ("📊  Monitor", "☁  Synchronizacja", "🕓  Historia"):
            tab.add(t)

        self._build_monitor(tab.tab("📊  Monitor"))
        self._build_sync(tab.tab("☁  Synchronizacja"))
        self._build_history(tab.tab("🕓  Historia"))

    # ── Monitor ───────────────────────────────────────────────────────────────

    def _build_monitor(self, parent):
        if not self._monitor.available:
            ctk.CTkLabel(parent,
                         text="psutil nie jest zainstalowany.\npip install psutil",
                         font=ctk.CTkFont(size=13), text_color="#555").pack(pady=40)
            return

        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=12)
        top.columnconfigure((0, 1), weight=1)

        ram_card = ctk.CTkFrame(top, corner_radius=12)
        ram_card.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(ram_card, text="🧠  RAM",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(12, 4))
        self._ram_lbl = ctk.CTkLabel(ram_card, text="– MB",
                                      font=ctk.CTkFont(size=24, weight="bold"),
                                      text_color="#2196F3")
        self._ram_lbl.pack()
        self._ram_bar = ctk.CTkProgressBar(ram_card, height=8, corner_radius=4,
                                            progress_color="#2196F3")
        self._ram_bar.pack(fill="x", padx=16, pady=(4, 12))
        self._ram_bar.set(0)

        cpu_card = ctk.CTkFrame(top, corner_radius=12)
        cpu_card.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(cpu_card, text="⚙  CPU",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(12, 4))
        self._cpu_lbl = ctk.CTkLabel(cpu_card, text="–%",
                                      font=ctk.CTkFont(size=24, weight="bold"),
                                      text_color="#FF6B35")
        self._cpu_lbl.pack()
        self._cpu_bar = ctk.CTkProgressBar(cpu_card, height=8, corner_radius=4,
                                            progress_color="#FF6B35")
        self._cpu_bar.pack(fill="x", padx=16, pady=(4, 12))
        self._cpu_bar.set(0)

        hist = ctk.CTkFrame(parent, corner_radius=10)
        hist.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(hist, text="Historia (ostatnie 40 pomiarów)",
                     font=ctk.CTkFont(size=11), text_color="#666").pack(
            anchor="w", padx=12, pady=(8, 4))
        self._sparkline = ctk.CTkLabel(hist,
                                        text="Uruchom monitoring aby zobaczyć historię.",
                                        font=ctk.CTkFont(family="Consolas", size=10),
                                        text_color="#444", anchor="w")
        self._sparkline.pack(fill="x", padx=12, pady=(0, 8))

        self._alert_lbl = ctk.CTkLabel(parent, text="",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color="#FF8C00")
        self._alert_lbl.pack()

        self._mon_btn = ctk.CTkButton(parent, text="▶ Start monitoringu", height=34,
                                       fg_color="#2a2a2a", hover_color="#555",
                                       command=self._toggle_monitor)
        self._mon_btn.pack(pady=8)
        self._monitor_running = False
        self._monitor.set_callback(self._on_resource_update)

    def _toggle_monitor(self):
        if not self._monitor_running:
            self._monitor.start()
            self._monitor_running = True
            self._mon_btn.configure(text="⏹ Stop monitoringu",
                                     fg_color="#aa2222", hover_color="#881111")
        else:
            self._monitor.stop()
            self._monitor_running = False
            self._mon_btn.configure(text="▶ Start monitoringu",
                                     fg_color="#2a2a2a", hover_color="#555")

    def _on_resource_update(self, snap):
        try:
            if not self.winfo_exists():
                return
            def _ui():
                if not self.winfo_exists():
                    return
                self._ram_lbl.configure(text=snap.ram_label())
                self._cpu_lbl.configure(text=snap.cpu_label())
                self._ram_bar.set(snap.ram_percent / 100)
                self._cpu_bar.set(snap.cpu_percent / 100)
                blocks = "▁▂▃▄▅▆▇█"
                def _spark(h):
                    if not h:
                        return ""
                    mx = max(h) or 1
                    return "".join(blocks[int(v / mx * 7)] for v in h[-40:])
                self._sparkline.configure(
                    text=f"CPU: {_spark(snap.cpu_history)}\n"
                         f"RAM: {_spark(snap.ram_history)}")
                self._alert_lbl.configure(text=self._monitor.get_alert() or "")
            self.after(0, _ui)
        except Exception:
            pass

    # ── Synchronizacja ────────────────────────────────────────────────────────

    def _build_sync(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.columnconfigure(0, weight=1)

        for row_i, (title, desc, stype) in enumerate([
            ("⚙ Synchronizacja ustawień",   "Instalacje i ustawienia w chmurze.",    "settings"),
            ("🌍 Synchronizacja światów",    "Kopie zapasowe światów Minecraft.",     "worlds"),
            ("📸 Synchronizacja screenshotów","Automatyczny backup screenshotów.",    "screenshots"),
        ]):
            card = ctk.CTkFrame(scroll, corner_radius=12)
            card.grid(row=row_i, column=0, sticky="ew", pady=6)
            ctk.CTkLabel(card, text=title,
                         font=ctk.CTkFont(size=13, weight="bold")).pack(
                anchor="w", padx=16, pady=(12, 4))
            ctk.CTkLabel(card, text=desc,
                         font=ctk.CTkFont(size=11), text_color="#888").pack(
                anchor="w", padx=16)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(4, 12))
            ctk.CTkButton(row, text="⬆ Wyślij", width=90, height=30,
                          fg_color="#FF6B35", hover_color="#e05520",
                          command=lambda s=stype: self._do_sync(s, "up")).pack(
                side="left", padx=(0, 6))
            ctk.CTkButton(row, text="⬇ Pobierz", width=90, height=30,
                          fg_color="#2196F3", hover_color="#1565C0",
                          command=lambda s=stype: self._do_sync(s, "down")).pack(side="left")

        self._sync_status = ctk.CTkLabel(scroll, text="",
                                          font=ctk.CTkFont(size=11), text_color="#888")
        self._sync_status.grid(row=3, column=0, pady=4)

    def _do_sync(self, sync_type, direction):
        token, _ = load_session()
        if not token:
            self._sync_status.configure(
                text="⚠ Zaloguj się aby synchronizować", text_color="#FF8C00")
            return
        inst      = self._get_inst() if self._get_inst else None
        inst_name = inst.get("name", "") if inst else ""
        self._sync_status.configure(text="⏳ Synchronizacja…", text_color="#888")

        def _run():
            fn = sync_to_server if direction == "up" else sync_from_server
            ok, msg = fn(token, sync_type, inst_name,
                         on_progress=lambda s: self.after(
                             0, lambda m=s: self._sync_status.configure(text=m)))
            col = "#4CAF50" if ok else "#FF4444"
            self.after(0, lambda: self._sync_status.configure(
                text=f"{'✅' if ok else '❌'} {msg}", text_color=col))

        threading.Thread(target=_run, daemon=True).start()

    # ── Historia ──────────────────────────────────────────────────────────────

    def _build_history(self, parent):
        top_row = ctk.CTkFrame(parent, fg_color="transparent")
        top_row.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(top_row, text="💾 Zapisz snapshot", height=32,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=self._save_snap).pack(side="left", padx=(0, 8))
        self._snap_entry = ctk.CTkEntry(top_row, placeholder_text="Etykieta (opcjonalna)",
                                         height=32, width=200)
        self._snap_entry.pack(side="left")

        self._hist_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self._hist_scroll.pack(fill="both", expand=True, pady=4)
        self._hist_scroll.columnconfigure(0, weight=1)

        self._hist_status = ctk.CTkLabel(parent, text="",
                                          font=ctk.CTkFont(size=11), text_color="#888")
        self._hist_status.pack(pady=4)
        self._refresh_history()

    def _save_snap(self):
        label = self._snap_entry.get().strip() or "Ręczny snapshot"
        save_config_snapshot(label)
        self._snap_entry.delete(0, "end")
        self._refresh_history()
        self._hist_status.configure(text="✅ Snapshot zapisany", text_color="#4CAF50")

    def _refresh_history(self):
        for w in self._hist_scroll.winfo_children():
            w.destroy()
        snaps = list_snapshots()
        if not snaps:
            ctk.CTkLabel(self._hist_scroll,
                         text="Brak snapshotów.\nKliknij 'Zapisz snapshot' aby zachować konfigurację.",
                         font=ctk.CTkFont(size=12), text_color="#555",
                         justify="center").grid(row=0, column=0, pady=40)
            return
        for i, snap in enumerate(snaps):
            self._snap_card(i, snap)

    def _snap_card(self, idx, snap):
        card = ctk.CTkFrame(self._hist_scroll, corner_radius=8, height=60)
        card.grid(row=idx, column=0, sticky="ew", pady=3)
        card.columnconfigure(1, weight=1)
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=snap["timestamp"][:16].replace("T", " "),
                     font=ctk.CTkFont(size=10), text_color="#555",
                     width=120).grid(row=0, column=0, padx=10, pady=(8, 0))
        ctk.CTkLabel(card, text=snap["label"],
                     font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(card, text=f"{snap['n_inst']} instalacji",
                     font=ctk.CTkFont(size=10), text_color="#666",
                     anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 8))
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=2, padx=8)
        ctk.CTkButton(btns, text="Przywróć", width=80, height=26,
                      fg_color="#2196F3", hover_color="#1565C0",
                      command=lambda p=snap["path"]: self._restore(p)).pack(pady=(0, 3))
        ctk.CTkButton(btns, text="✕", width=28, height=26,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      command=lambda p=snap["path"]: (
                          delete_snapshot(p), self._refresh_history()
                      )).pack()

    def _restore(self, path):
        ok = restore_snapshot(path)
        self._hist_status.configure(
            text="✅ Przywrócono! Uruchom launcher ponownie." if ok else "❌ Błąd przywracania",
            text_color="#4CAF50" if ok else "#FF4444")

    # ── gate (bramka) ─────────────────────────────────────────────────────────

    def on_show(self, **_):
        user = self._get_user_info() if self._get_user_info else None
        if not is_premium(user):
            self._show_gate()
        else:
            self._hide_gate()
            self._refresh_history()

    def _show_gate(self):
        if self._gate and self._gate.winfo_exists():
            return
        self._gate = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self._gate.place(relx=0, rely=0, relwidth=1, relheight=1)

        box = ctk.CTkFrame(self._gate, corner_radius=20)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(box, text="✨",
                     font=ctk.CTkFont(size=52)).pack(pady=(30, 4))
        ctk.CTkLabel(box, text="Moddy Premium",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#FFD700").pack()
        ctk.CTkLabel(box,
                     text="Zaloguj się aby odblokować wszystkie funkcje.",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(pady=(4, 0))

        feats = ctk.CTkFrame(box, fg_color="transparent")
        feats.pack(padx=40, pady=(12, 8))
        for f in [
            "📊  Monitor RAM i CPU",
            "☁  Synchronizacja z chmurą",
            "📸  Backup screenshotów",
            "🕓  Historia konfiguracji",
        ]:
            ctk.CTkLabel(feats, text=f, font=ctk.CTkFont(size=12),
                         text_color="#aaa", anchor="w").pack(anchor="w", pady=2)

        ctk.CTkButton(box, text="Zaloguj się", height=42, width=200,
                      fg_color="#4285F4", hover_color="#2b6dd4",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: self._navigate("login")).pack(pady=(12, 24))

    def _hide_gate(self):
        if self._gate and self._gate.winfo_exists():
            self._gate.destroy()
            self._gate = None
