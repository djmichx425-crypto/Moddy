"""
Security Center — weryfikacja plików, skanowanie modów, ostrzeżenia.
"""
import threading
import customtkinter as ctk

from ...core.integrity_checker import verify_all_library, scan_all_library, IntegrityResult
from ...core.mod_library import list_mods


class SecurityPage(ctk.CTkFrame):

    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="🔒  Security Center",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        tab = ctk.CTkTabview(self, corner_radius=8)
        tab.pack(fill="both", expand=True, padx=16, pady=10)
        tab.add("🔍  Weryfikacja plików")
        tab.add("🦠  Skanowanie modów")

        self._build_verify(tab.tab("🔍  Weryfikacja plików"))
        self._build_scan(tab.tab("🦠  Skanowanie modów"))

    # ── weryfikacja ───────────────────────────────────────────────────────────

    def _build_verify(self, parent):
        desc = ctk.CTkFrame(parent, corner_radius=10)
        desc.pack(fill="x", pady=(8, 10))
        ctk.CTkLabel(desc,
                     text="Weryfikacja sprawdza czy pliki modów nie zostały zmodyfikowane\n"
                          "od momentu pobrania (porównanie SHA-256).",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=10)

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(btn_row, text="🔍 Weryfikuj wszystkie mody",
                      height=36, width=200,
                      fg_color="#2a2a5a", hover_color="#3a3a8a",
                      command=self._run_verify).pack(side="left")
        self._verify_status = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=11), text_color="#888")
        self._verify_status.pack(side="left", padx=12)

        self._verify_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent")
        self._verify_scroll.pack(fill="both", expand=True)
        self._verify_scroll.columnconfigure(0, weight=1)

    def _run_verify(self):
        self._verify_status.configure(text="⏳ Sprawdzam…", text_color="#888")
        for w in self._verify_scroll.winfo_children():
            w.destroy()

        def _worker():
            results = verify_all_library()
            self.after(0, lambda: self._show_verify_results(results))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_verify_results(self, results: list[IntegrityResult]):
        ok   = sum(1 for r in results if r.status == "ok")
        bad  = len(results) - ok

        color = "#4CAF50" if bad == 0 else "#FF4444"
        self._verify_status.configure(
            text=f"✅ {ok} OK  {'❌ ' + str(bad) + ' problemy' if bad else ''}",
            text_color=color)

        for r in results:
            self._make_result_row(self._verify_scroll, r)

    # ── skanowanie ────────────────────────────────────────────────────────────

    def _build_scan(self, parent):
        desc = ctk.CTkFrame(parent, corner_radius=10)
        desc.pack(fill="x", pady=(8, 10))
        ctk.CTkLabel(desc,
                     text="Skanowanie analizuje zawartość plików JAR w poszukiwaniu:\n"
                          "keyloggerów, minerów kryptowalut, RAT, wykradaczy tokenów Discord.",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=10)

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(btn_row, text="🦠 Skanuj bibliotekę modów",
                      height=36, width=210,
                      fg_color="#5a2a2a", hover_color="#8a3a3a",
                      command=self._run_scan).pack(side="left")
        self._scan_status = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=11), text_color="#888")
        self._scan_status.pack(side="left", padx=12)

        self._scan_scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent")
        self._scan_scroll.pack(fill="both", expand=True)
        self._scan_scroll.columnconfigure(0, weight=1)

    def _run_scan(self):
        self._scan_status.configure(text="⏳ Skanuję…", text_color="#888")
        for w in self._scan_scroll.winfo_children():
            w.destroy()

        def _worker():
            suspicious = scan_all_library()
            mods = list_mods()
            self.after(0, lambda: self._show_scan_results(suspicious, len(mods)))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_scan_results(self, suspicious: list[IntegrityResult], total: int):
        if not suspicious:
            self._scan_status.configure(
                text=f"✅ Czysto! {total} modów przeskanowano — brak zagrożeń.",
                text_color="#4CAF50")
            ctk.CTkLabel(self._scan_scroll,
                         text="✅ Wszystkie mody są bezpieczne.",
                         font=ctk.CTkFont(size=13), text_color="#4CAF50").pack(pady=30)
        else:
            self._scan_status.configure(
                text=f"⚠ {len(suspicious)} podejrzanych modów!",
                text_color="#FF4444")
            for r in suspicious:
                self._make_suspicious_card(r)

    def _make_suspicious_card(self, r: IntegrityResult):
        card = ctk.CTkFrame(self._scan_scroll, corner_radius=10,
                            border_width=2, border_color="#FF4444")
        card.pack(fill="x", pady=5)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(hdr, text="⚠ " + r.filename,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#FF4444").pack(side="left")
        ctk.CTkLabel(hdr, text=r.message,
                     font=ctk.CTkFont(size=10), text_color="#FF8C00").pack(
            side="left", padx=8)

        for threat in r.threats[:6]:
            ctk.CTkLabel(card, text=f"  • {threat}",
                         font=ctk.CTkFont(size=10), text_color="#FF8C00",
                         anchor="w").pack(fill="x", padx=16, pady=1)

        ctk.CTkButton(card, text="Usuń mod", height=28, width=90,
                      fg_color="#aa2222", hover_color="#881111",
                      command=lambda fn=r.filename: self._remove_mod(fn)).pack(
            anchor="e", padx=12, pady=(4, 10))

    # ── helper rows ───────────────────────────────────────────────────────────

    def _make_result_row(self, parent, r: IntegrityResult):
        STATUS_INFO = {
            "ok":       ("✅", "#4CAF50", "OK"),
            "modified": ("❌", "#FF4444", "ZMODYFIKOWANY"),
            "missing":  ("⚠", "#FF8C00", "BRAK PLIKU"),
        }
        icon, color, label = STATUS_INFO.get(r.status, ("?", "#666", r.status))

        row = ctk.CTkFrame(parent, corner_radius=6, height=42)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(row, text=icon, width=24,
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=8)
        ctk.CTkLabel(row, text=r.filename,
                     font=ctk.CTkFont(size=11), anchor="w").pack(
            side="left", fill="x", expand=True)
        ctk.CTkLabel(row, text=label, width=110,
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=color).pack(side="left")
        if r.message and r.status != "ok":
            ctk.CTkLabel(row, text=r.message[:40],
                         font=ctk.CTkFont(size=9), text_color="#666").pack(
                side="left", padx=4)

    def _remove_mod(self, filename: str):
        from ...core.mod_library import remove_mod
        remove_mod(filename)
        for w in self._scan_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._scan_scroll,
                     text=f"✅ Usunięto: {filename}",
                     font=ctk.CTkFont(size=12), text_color="#4CAF50").pack(pady=20)

    def on_show(self, **_):
        pass
