import customtkinter as ctk

from ...core.minecraft_launcher import is_installed


LOADER_COLORS = {
    "vanilla":  "#4CAF50",
    "forge":    "#A0522D",
    "fabric":   "#7EB5D6",
    "quilt":    "#9370DB",
    "neoforge": "#FF8C00",
}


class HomePage(ctk.CTkFrame):
    def __init__(self, parent, navigate, get_installations,
                 save_installations, on_select=None, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._get_installations = get_installations
        self._save_installations = save_installations
        self._on_select = on_select          # callback → main_window._select_installation
        self._selected_inst: dict | None = None
        self._cards: list[tuple[dict, ctk.CTkFrame]] = []
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")

        ctk.CTkLabel(top, text="Twoje instalacje",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        ctk.CTkButton(top, text="＋  Nowa instalacja", height=32,
                      fg_color="#FF6B35", hover_color="#e05520",
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._navigate("wizard")).pack(
            side="right", padx=16, pady=10)

        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=14, pady=10)
        self._scroll.columnconfigure(0, weight=1)

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._cards.clear()
        for w in self._scroll.winfo_children():
            w.destroy()

        installations = self._get_installations()
        if not installations:
            self._show_empty()
            return

        for i, inst in enumerate(installations):
            self._make_card(i, inst)

    def set_selected(self, inst: dict | None):
        """Zewnętrzne ustawienie aktywnej instalacji (z bottom bara)."""
        self._selected_inst = inst
        self._redraw_borders()

    # ── cards ─────────────────────────────────────────────────────────────────

    def _make_card(self, idx: int, inst: dict):
        installed = is_installed(inst)
        loader = (inst.get("loader") or "vanilla").lower()
        color = LOADER_COLORS.get(loader, "#555")
        is_sel = self._selected_inst is inst

        card = ctk.CTkFrame(
            self._scroll, corner_radius=10, height=96,
            border_width=2,
            border_color="#FF6B35" if is_sel else "#2a2a2a")
        card.grid(row=idx, column=0, sticky="ew", padx=4, pady=5)
        card.columnconfigure(1, weight=1)
        card.grid_propagate(False)

        # Kliknięcie karty = wybór + otwórz przeglądarkę modów
        for widget in (card,):
            widget.bind("<Button-1>", lambda e, i=inst, c=card: self._click_card(i, c))
        card.configure(cursor="hand2")

        # ── badge loadera ──────────────────────────────────────────────────
        left = ctk.CTkFrame(card, fg_color="transparent", width=88)
        left.grid(row=0, column=0, rowspan=3, padx=(12, 6), pady=10, sticky="ns")
        left.pack_propagate(False)

        ctk.CTkLabel(left, text=loader.upper(),
                     font=ctk.CTkFont(size=10, weight="bold"),
                     fg_color=color, corner_radius=5,
                     text_color="white", width=80, height=24).pack()

        if installed:
            ctk.CTkLabel(left, text="✓ gotowe",
                         font=ctk.CTkFont(size=9),
                         text_color="#4CAF50").pack(pady=(3, 0))
        else:
            ctk.CTkLabel(left, text="⬇ do pobrania",
                         font=ctk.CTkFont(size=9),
                         text_color="#FF8C00").pack(pady=(3, 0))

        # ── nazwa i szczegóły ──────────────────────────────────────────────
        ctk.CTkLabel(card,
                     text=inst.get("name", "Instalacja"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(14, 0))

        ver = inst.get("version") or inst.get("game_version", "?")
        mem = inst.get("memory_mb", 2048)
        created = inst.get("created", "")[:10]
        ctk.CTkLabel(card,
                     text=f"Minecraft {ver}   •   {mem} MB RAM   •   {created}   "
                          f"{'✓ zainstalowane' if installed else '⬇ do pobrania'}",
                     font=ctk.CTkFont(size=10),
                     text_color="#666", anchor="w").grid(
            row=1, column=1, sticky="w")

        ctk.CTkLabel(card, text="Kliknij aby przeglądać mody →",
                     font=ctk.CTkFont(size=9), text_color="#444",
                     anchor="w").grid(row=2, column=1, sticky="w", pady=(0, 8))

        # ── usuń ──────────────────────────────────────────────────────────
        ctk.CTkButton(card, text="✕", width=28, height=28,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      font=ctk.CTkFont(size=11),
                      command=lambda ix=idx: self._delete(ix)).grid(
            row=0, column=2, rowspan=2, padx=10)

        self._cards.append((inst, card))

    def _click_card(self, inst: dict, card: ctk.CTkFrame):
        self._selected_inst = inst
        self._redraw_borders()
        if self._on_select:
            self._on_select(inst)

    def _redraw_borders(self):
        for inst, card in self._cards:
            is_sel = inst is self._selected_inst
            try:
                card.configure(
                    border_width=2,
                    border_color="#FF6B35" if is_sel else "#2a2a2a")
            except Exception:
                pass

    # ── empty state ───────────────────────────────────────────────────────────

    def _show_empty(self):
        box = ctk.CTkFrame(self._scroll, fg_color="transparent")
        box.grid(row=0, column=0, pady=60)
        ctk.CTkLabel(box, text="⛏",
                     font=ctk.CTkFont(size=56)).pack()
        ctk.CTkLabel(box, text="Zacznij od wyboru wersji",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#555").pack(pady=(8, 4))
        for step in ["1.  Utwórz instalację (wybierz Minecraft + loader)",
                     "2.  Przeglądaj i pobierz mody dla tej wersji",
                     "3.  Kliknij ▶ GRAJ — launcher zainstaluje i uruchomi grę"]:
            ctk.CTkLabel(box, text=step,
                         font=ctk.CTkFont(size=12), text_color="#555").pack(anchor="w")
        ctk.CTkButton(box, text="＋  Nowa instalacja", height=42, width=220,
                      fg_color="#FF6B35", hover_color="#e05520",
                      font=ctk.CTkFont(size=14),
                      command=lambda: self._navigate("wizard")).pack(pady=20)

    # ── delete ────────────────────────────────────────────────────────────────

    def _delete(self, idx: int):
        installations = self._get_installations()
        removed = installations[idx]
        installations.pop(idx)
        self._save_installations(installations)
        if self._selected_inst is removed:
            self._selected_inst = installations[0] if installations else None
            if self._on_select:
                self._on_select(self._selected_inst)
        self.on_show()
