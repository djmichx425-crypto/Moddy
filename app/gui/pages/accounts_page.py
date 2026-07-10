"""
Menedżer kont Minecraft.
"""
import tkinter as tk
import customtkinter as ctk
import webbrowser

from ...core.accounts_manager import (
    get_accounts, get_selected_account,
    add_offline_account, remove_account,
    set_selected, rename_account,
)

# Kolory awatarów (przypisywane z hashu nazwy)
AVATAR_COLORS = [
    "#FF6B35", "#4CAF50", "#2196F3", "#9C27B0",
    "#FF9800", "#00BCD4", "#E91E63", "#607D8B",
    "#8BC34A", "#F44336", "#3F51B5", "#009688",
]


def _avatar_color(username: str) -> str:
    return AVATAR_COLORS[abs(hash(username)) % len(AVATAR_COLORS)]


def _initials(username: str) -> str:
    parts = username.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return username[:2].upper() if len(username) >= 2 else username.upper()


class _Avatar(tk.Canvas):
    """Kolorowy kwadrat z inicjałami gracza."""
    def __init__(self, parent, username: str, size: int = 56, **kwargs):
        super().__init__(parent, width=size, height=size,
                         highlightthickness=0, **kwargs)
        color = _avatar_color(username)
        inits = _initials(username)
        r = size // 6
        self.create_rectangle(0, 0, size, size, fill=color, outline="")
        # zaokrąglenie — narożniki ciemniejsze
        self.create_rectangle(0, 0, r, r, fill=self["bg"] or "#2b2b2b", outline="")
        self.create_rectangle(size-r, 0, size, r, fill=self["bg"] or "#2b2b2b", outline="")
        self.create_rectangle(0, size-r, r, size, fill=self["bg"] or "#2b2b2b", outline="")
        self.create_rectangle(size-r, size-r, size, size, fill=self["bg"] or "#2b2b2b", outline="")
        fs = max(10, size // 3)
        self.create_text(size // 2, size // 2, text=inits,
                         fill="white", font=("Arial", fs, "bold"))


class AccountsPage(ctk.CTkFrame):

    def __init__(self, parent, navigate, on_change=None, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate  = navigate
        self._on_change = on_change
        self._editing_uuid: str | None = None
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # nagłówek
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="👤  Konta Minecraft",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        # scroll główny
        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        self._scroll.columnconfigure(0, weight=1)

        # dolna belka: dodaj + Microsoft
        self._build_bottom()

    def _build_bottom(self):
        bottom = ctk.CTkFrame(self, corner_radius=0, fg_color="#161616")
        bottom.pack(fill="x", padx=0, pady=0)

        # Dodaj offline
        add_row = ctk.CTkFrame(bottom, fg_color="transparent")
        add_row.pack(fill="x", padx=16, pady=10)

        self._name_entry = ctk.CTkEntry(
            add_row, placeholder_text="Nowa nazwa gracza (min. 3 znaki)…",
            height=36, font=ctk.CTkFont(size=13))
        self._name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._name_entry.bind("<Return>", lambda e: self._add_offline())

        ctk.CTkButton(add_row, text="+ Dodaj offline", width=120, height=36,
                      fg_color="#4CAF50", hover_color="#388E3C",
                      font=ctk.CTkFont(size=12),
                      command=self._add_offline).pack(side="left", padx=(0, 6))

        ctk.CTkButton(add_row, text="🎮 Microsoft", width=110, height=36,
                      fg_color="#0078D4", hover_color="#005fa3",
                      font=ctk.CTkFont(size=12),
                      command=self._ms_login).pack(side="left")

        self._msg = ctk.CTkLabel(bottom, text="",
                                  font=ctk.CTkFont(size=11), text_color="#4CAF50")
        self._msg.pack(anchor="w", padx=16, pady=(0, 8))

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._editing_uuid = None
        self._msg.configure(text="")
        self._refresh()

    def _refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        accounts = get_accounts()
        selected = get_selected_account()
        sel_uuid = selected["uuid"] if selected else None

        if not accounts:
            self._show_empty()
            return

        # Aktywne konto — duża karta na górze
        if selected:
            self._make_hero_card(selected)

        # Separator
        ctk.CTkLabel(self._scroll,
                     text=f"WSZYSTKIE KONTA  ({len(accounts)})",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(anchor="w", pady=(14, 6))

        # Siatka kont
        grid = ctk.CTkFrame(self._scroll, fg_color="transparent")
        grid.pack(fill="x")

        COLS = 4
        for i, acc in enumerate(accounts):
            self._make_grid_card(grid, acc, sel_uuid, i, COLS)

        # Karta "Dodaj" jako ostatnia w siatce
        idx = len(accounts)
        col = idx % COLS
        row = idx // COLS
        self._make_add_card(grid, row, col)

    # ── hero card (aktywne konto) ─────────────────────────────────────────────

    def _make_hero_card(self, acc: dict):
        card = ctk.CTkFrame(self._scroll, corner_radius=14,
                            border_width=2, border_color="#FF6B35")
        card.pack(fill="x", pady=(0, 4))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        # Awatar duży
        bg = self._get_bg(card)
        av = _Avatar(inner, acc["username"], size=72, bg=bg)
        av.pack(side="left", padx=(0, 16))

        # Info
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        # Nazwa + edycja
        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(anchor="w")

        if self._editing_uuid == acc["uuid"]:
            self._edit_entry = ctk.CTkEntry(name_row, width=200, height=32,
                                             font=ctk.CTkFont(size=16))
            self._edit_entry.insert(0, acc["username"])
            self._edit_entry.pack(side="left")
            self._edit_entry.bind("<Return>", lambda e, u=acc["uuid"]: self._save_rename(u))
            self._edit_entry.bind("<Escape>", lambda e: self._cancel_edit())
            self._edit_entry.focus()
            ctk.CTkButton(name_row, text="✓", width=30, height=30,
                          fg_color="#4CAF50", hover_color="#388E3C",
                          command=lambda u=acc["uuid"]: self._save_rename(u)).pack(
                side="left", padx=(4, 0))
            ctk.CTkButton(name_row, text="✕", width=30, height=30,
                          fg_color="#3a3a3a", hover_color="#555",
                          command=self._cancel_edit).pack(side="left", padx=2)
        else:
            ctk.CTkLabel(name_row, text=acc["username"],
                         font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
            ctk.CTkButton(name_row, text="✎", width=28, height=28,
                          fg_color="transparent", hover_color="#2a2a2a",
                          text_color="#888",
                          command=lambda u=acc["uuid"]: self._start_edit(u)).pack(
                side="left", padx=(6, 0))

        # Typ + badge
        type_text  = "Microsoft" if acc.get("type") == "microsoft" else "Offline"
        type_color = "#0078D4" if acc.get("type") == "microsoft" else "#888"
        badge_row = ctk.CTkFrame(info, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(badge_row, text=type_text,
                     font=ctk.CTkFont(size=11), text_color=type_color).pack(side="left")
        ctk.CTkLabel(badge_row, text="  ✓ Aktywne",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#FF6B35").pack(side="left")

        # UUID
        ctk.CTkLabel(info, text=acc["uuid"][:18] + "…",
                     font=ctk.CTkFont(size=9), text_color="#444").pack(anchor="w")

        # Usunięcie
        ctk.CTkButton(inner, text="Usuń konto", width=96, height=28,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      font=ctk.CTkFont(size=10),
                      command=lambda u=acc["uuid"]: self._remove(u)).pack(
            side="right", anchor="n")

    # ── grid card ─────────────────────────────────────────────────────────────

    def _make_grid_card(self, parent, acc: dict, sel_uuid: str | None,
                        idx: int, cols: int):
        col = idx % cols
        row = idx // cols
        is_sel = acc["uuid"] == sel_uuid

        card = ctk.CTkFrame(parent, corner_radius=12, width=140, height=150,
                            border_width=2,
                            border_color="#FF6B35" if is_sel else "#2a2a2a",
                            cursor="hand2")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        card.grid_propagate(False)

        bg = self._get_bg(card)
        av = _Avatar(card, acc["username"], size=52, bg=bg)
        av.pack(pady=(14, 6))

        ctk.CTkLabel(card, text=acc["username"][:12],
                     font=ctk.CTkFont(size=11, weight="bold"),
                     anchor="center").pack()

        type_text  = "MS" if acc.get("type") == "microsoft" else "Offline"
        type_color = "#0078D4" if acc.get("type") == "microsoft" else "#666"
        ctk.CTkLabel(card, text=type_text,
                     font=ctk.CTkFont(size=9), text_color=type_color).pack()

        if not is_sel:
            ctk.CTkButton(card, text="Wybierz", height=24, width=90,
                          fg_color="#3a3a3a", hover_color="#FF6B35",
                          font=ctk.CTkFont(size=10),
                          command=lambda u=acc["uuid"]: self._select(u)).pack(pady=(4, 0))

        # kliknięcie całej karty = wybierz
        for w in card.winfo_children():
            w.bind("<Button-1>", lambda e, u=acc["uuid"]: self._select(u))
        card.bind("<Button-1>", lambda e, u=acc["uuid"]: self._select(u))

    def _make_add_card(self, parent, row: int, col: int):
        card = ctk.CTkFrame(parent, corner_radius=12, width=140, height=150,
                            fg_color="#1e1e1e", border_width=1,
                            border_color="#2a2a2a", cursor="hand2")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.grid_propagate(False)

        ctk.CTkLabel(card, text="+",
                     font=ctk.CTkFont(size=34), text_color="#444").pack(pady=(24, 4))
        ctk.CTkLabel(card, text="Dodaj konto",
                     font=ctk.CTkFont(size=10), text_color="#555").pack()

        card.bind("<Button-1>", lambda e: self._name_entry.focus())
        card.configure(fg_color="#1e1e1e")

    # ── empty ─────────────────────────────────────────────────────────────────

    def _show_empty(self):
        box = ctk.CTkFrame(self._scroll, fg_color="transparent")
        box.pack(pady=60)
        ctk.CTkLabel(box, text="👤",
                     font=ctk.CTkFont(size=52)).pack()
        ctk.CTkLabel(box, text="Brak kont",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#555").pack(pady=(8, 4))
        ctk.CTkLabel(box, text="Dodaj konto offline poniżej aby grać.",
                     font=ctk.CTkFont(size=12), text_color="#444").pack()

    # ── actions ───────────────────────────────────────────────────────────────

    def _add_offline(self):
        name = self._name_entry.get().strip()
        try:
            add_offline_account(name)
            self._name_entry.delete(0, "end")
            self._msg.configure(text=f"✓ Dodano: {name}", text_color="#4CAF50")
            self.after(2500, lambda: self._msg.configure(text=""))
            self._refresh()
            if self._on_change:
                self._on_change()
        except ValueError as e:
            self._msg.configure(text=str(e), text_color="#FF6B35")

    def _select(self, acc_uuid: str):
        set_selected(acc_uuid)
        self._refresh()
        if self._on_change:
            self._on_change()

    def _remove(self, acc_uuid: str):
        remove_account(acc_uuid)
        self._editing_uuid = None
        self._refresh()
        if self._on_change:
            self._on_change()

    def _start_edit(self, acc_uuid: str):
        self._editing_uuid = acc_uuid
        self._refresh()

    def _cancel_edit(self):
        self._editing_uuid = None
        self._refresh()

    def _save_rename(self, acc_uuid: str):
        new_name = self._edit_entry.get().strip()
        if rename_account(acc_uuid, new_name):
            self._editing_uuid = None
            self._refresh()
            if self._on_change:
                self._on_change()
            self._msg.configure(text=f"✓ Zmieniono nazwę na: {new_name}",
                                  text_color="#4CAF50")
            self.after(2500, lambda: self._msg.configure(text=""))
        else:
            self._msg.configure(text="Nazwa min. 3 znaki", text_color="#FF6B35")

    def _ms_login(self):
        webbrowser.open("https://login.live.com/")
        self._msg.configure(
            text="⚠ Logowanie Microsoft wymaga własnej Azure App (discord.com/developers).\n"
                 "Na razie użyj konta offline.",
            text_color="#FFD700")

    # ── helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_bg(widget) -> str:
        try:
            fg = widget.cget("fg_color")
            if isinstance(fg, (list, tuple)):
                import customtkinter as ctk
                return fg[0] if ctk.get_appearance_mode() == "Light" else fg[1]
            return str(fg)
        except Exception:
            return "#2b2b2b"
