"""
Generator paczek modów oparty na AI (GPT-OSS-120B przez OpenRouter).
Interfejs czatu z live streamingiem odpowiedzi.
"""
import tkinter as tk
import customtkinter as ctk
import threading
from datetime import datetime

from ...core.ai_generator import stream_chat, extract_mod_names, build_messages
from ...core.mod_library import load_settings, save_settings

OPENROUTER_KEY_DEFAULT = ""

SUGGESTIONS = [
    "Zaproponuj mody do survival z realizmem dla Fabric 1.20.1",
    "Jakie mody poprawią wydajność Minecraft?",
    "Chcę grać w magię i RPG, co polecasz?",
    "Mody do technologicznej gry z automatyzacją",
    "Mody PvP i walki na serwery multiplayer",
    "Piękne shadery i optymalizacja dla słabego PC",
]


class AIGeneratorPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 get_active_installation=None,
                 on_search_mod=None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate             = navigate
        self._get_inst             = get_active_installation
        self._on_search_mod        = on_search_mod
        self._history: list[dict]  = []
        self._streaming            = False
        self._last_ai_text         = ""
        self._extracted_mods: list[dict] = []
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # nagłówek
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="🤖  AI Generator Paczek",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)
        ctk.CTkLabel(top, text="GPT-OSS-120B • OpenRouter",
                     font=ctk.CTkFont(size=10), text_color="#555").pack(
            side="left", padx=4)

        # Główna treść — lewa (czat) + prawa (rekomendacje)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_chat(body)
        self._build_sidebar(body)

    def _build_chat(self, parent):
        chat_frame = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        chat_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        # Historia czatu
        self._chat_box = ctk.CTkTextbox(
            chat_frame, wrap="word",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#111", text_color="#ddd",
            state="disabled")
        self._chat_box.grid(row=0, column=0, sticky="nsew")
        self._chat_box.tag_config("user",  foreground="#FF6B35")
        self._chat_box.tag_config("ai",    foreground="#ddd")
        self._chat_box.tag_config("mod",   foreground="#4CAF50")
        self._chat_box.tag_config("meta",  foreground="#888")

        # Szybkie sugestie
        sug_frame = ctk.CTkFrame(chat_frame, fg_color="#161616", corner_radius=8)
        sug_frame.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(sug_frame, text="Szybkie pytania:",
                     font=ctk.CTkFont(size=10), text_color="#555").pack(
            anchor="w", padx=8, pady=(6, 2))
        sug_row = ctk.CTkFrame(sug_frame, fg_color="transparent")
        sug_row.pack(fill="x", padx=6, pady=(0, 6))
        for sug in SUGGESTIONS[:3]:
            ctk.CTkButton(sug_row, text=sug[:40] + "…" if len(sug) > 40 else sug,
                          height=24, fg_color="#2a2a2a", hover_color="#FF6B35",
                          font=ctk.CTkFont(size=10),
                          command=lambda s=sug: self._send(s)).pack(
                side="left", padx=3, pady=2)

        # Pole wejściowe
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        input_frame.columnconfigure(0, weight=1)

        self._input = ctk.CTkTextbox(input_frame, height=60, wrap="word",
                                      font=ctk.CTkFont(size=12))
        self._input.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._input.bind("<Return>",     self._on_enter)
        self._input.bind("<Shift-Return>", lambda e: None)

        btn_col = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_col.grid(row=0, column=1)

        self._send_btn = ctk.CTkButton(
            btn_col, text="Wyślij ▶", width=90, height=28,
            fg_color="#FF6B35", hover_color="#e05520",
            font=ctk.CTkFont(size=12),
            command=lambda: self._send(self._input.get("1.0", "end").strip()))
        self._send_btn.pack(pady=(0, 4))

        self._retry_btn = ctk.CTkButton(
            btn_col, text="↩ Ponów", width=90, height=26,
            fg_color="#FF8C00", hover_color="#e07000",
            state="disabled",
            command=self._retry)
        self._retry_btn.pack(pady=(0, 4))

        ctk.CTkButton(btn_col, text="Wyczyść", width=90, height=26,
                      fg_color="#2a2a2a", hover_color="#555",
                      command=self._clear).pack()

        self._status_lbl = ctk.CTkLabel(
            chat_frame, text="", font=ctk.CTkFont(size=10), text_color="#555")
        self._status_lbl.grid(row=3, column=0, sticky="w", pady=2)

    def _build_sidebar(self, parent):
        side = ctk.CTkFrame(parent, corner_radius=8, fg_color="#161616")
        side.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)

        ctk.CTkLabel(side, text="🎮 Rekomendacje",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(12, 4), padx=12, anchor="w")
        ctk.CTkLabel(side,
                     text="AI automatycznie wykrywa\npolecane mody z odpowiedzi.",
                     font=ctk.CTkFont(size=10), text_color="#555",
                     justify="left").pack(padx=12, anchor="w")

        self._recs_scroll = ctk.CTkScrollableFrame(
            side, fg_color="transparent", corner_radius=0)
        self._recs_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkButton(side, text="📥 Pobierz wszystkie",
                      height=32, fg_color="#2a7a4a", hover_color="#1f5c37",
                      command=self._download_all_recs).pack(
            fill="x", padx=8, pady=(0, 8))

        # Klucz API
        api_frame = ctk.CTkFrame(side, fg_color="#111", corner_radius=6)
        api_frame.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(api_frame, text="OpenRouter API Key",
                     font=ctk.CTkFont(size=9), text_color="#555").pack(
            anchor="w", padx=8, pady=(6, 0))
        self._api_key_entry = ctk.CTkEntry(api_frame, show="*", height=26,
                                            font=ctk.CTkFont(size=10))
        self._api_key_entry.pack(fill="x", padx=8, pady=(2, 4))
        ctk.CTkButton(api_frame, text="Zapisz", height=24,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=self._save_api_key).pack(padx=8, pady=(0, 6), fill="x")

    # ── chat logic ────────────────────────────────────────────────────────────

    def on_show(self, **_):
        s = load_settings()
        key = s.get("openrouter_key", OPENROUTER_KEY_DEFAULT)
        self._api_key_entry.delete(0, "end")
        self._api_key_entry.insert(0, key)
        if not self._history:
            s = load_settings()
            has_key = bool(s.get("openrouter_key", "").strip())
            if has_key:
                self._append_chat(
                    "🤖 Cześć! Opisz jaki styl gry lubisz, a dobiorę dla Ciebie mody.\n"
                    "Możesz też zapytać o konkretne typy modów.\n\n", "ai")
            else:
                self._append_chat(
                    "🤖 Cześć! Aby korzystać z AI generatora, wklej swój klucz\n"
                    "OpenRouter API w polu poniżej (openrouter.ai → Keys → Create Key).\n"
                    "Model GPT-OSS-120B jest darmowy po rejestracji.\n\n", "meta")

    def _save_api_key(self):
        key = self._api_key_entry.get().strip()
        s = load_settings()
        s["openrouter_key"] = key
        save_settings(s)

    def _on_enter(self, event):
        if event.state & 0x1:   # Shift held → nowa linia
            return
        text = self._input.get("1.0", "end").strip()
        if text:
            self._send(text)
        return "break"

    def _send(self, text: str):
        if self._streaming or not text.strip():
            return
        self._input.delete("1.0", "end")

        # Pokaż wiadomość użytkownika
        self._append_chat(f"\n👤 Ty:  ", "user")
        self._append_chat(text + "\n", "ai")

        inst = self._get_inst() if self._get_inst else None
        loader  = inst.get("loader", "") if inst else ""
        mc_ver  = (inst.get("version") or inst.get("game_version", "")) if inst else ""

        messages = build_messages(self._history, text, loader, mc_ver)
        self._history.append({"role": "user", "content": text})

        s = load_settings()
        api_key = s.get("openrouter_key", "").strip()
        if not api_key:
            self._append_chat(
                "\n⚠ Brak klucza OpenRouter API.\n"
                "Wklej swój klucz w polu poniżej (openrouter.ai → Keys).\n", "meta")
            self._streaming = False
            self._send_btn.configure(state="normal", text="Wyślij ▶")
            self._status_lbl.configure(text="")
            return

        self._streaming = True
        self._send_btn.configure(state="disabled", text="⏳")
        self._status_lbl.configure(text="AI pisze…")
        self._last_ai_text = ""

        self._append_chat("\n🤖 AI:  ", "ai")

        def _stream():
            full = ""
            for token in stream_chat(messages, api_key):
                full += token
                self._last_ai_text = full
                self.after(0, lambda t=token: self._append_chat(t, "ai"))

            self._history.append({"role": "assistant", "content": full})
            mods = extract_mod_names(full)
            self._extracted_mods = mods
            self.after(0, lambda: self._on_stream_done(full, mods))

        threading.Thread(target=_stream, daemon=True).start()

    def _on_stream_done(self, full_text: str, mods: list[dict]):
        self._streaming = False
        self._send_btn.configure(state="normal", text="Wyślij ▶")
        self._append_chat("\n", "ai")

        is_error = full_text.strip().startswith("⚠")

        if is_error:
            self._status_lbl.configure(
                text="↩ Kliknij 'Spróbuj ponownie' lub wyślij wiadomość jeszcze raz",
                text_color="#FF8C00")
            self._retry_btn.configure(state="normal")
        elif mods:
            self._append_chat(
                f"\n✅ Wykryto {len(mods)} modów — kliknij aby wyszukać:\n", "meta")
            self._refresh_recs(mods)
            self._status_lbl.configure(
                text=f"✅ {len(mods)} modów w rekomendacjach",
                text_color="#4CAF50")
            self._retry_btn.configure(state="disabled")
        else:
            self._status_lbl.configure(text="", text_color="#555")
            self._retry_btn.configure(state="disabled")

    def _append_chat(self, text: str, tag: str = "ai"):
        self._chat_box.configure(state="normal")
        self._chat_box.insert("end", text, tag)
        self._chat_box.see("end")
        self._chat_box.configure(state="disabled")

    def _retry(self):
        """Ponów ostatnią wiadomość użytkownika."""
        self._retry_btn.configure(state="disabled")
        # Znajdź ostatnią wiadomość użytkownika w historii
        for msg in reversed(self._history):
            if msg["role"] == "user":
                # Usuń ostatnią odpowiedź AI z historii (była błędem)
                if self._history and self._history[-1]["role"] == "assistant":
                    self._history.pop()
                self._send(msg["content"])
                return

    def _clear(self):
        self._history.clear()
        self._extracted_mods.clear()
        self._chat_box.configure(state="normal")
        self._chat_box.delete("1.0", "end")
        self._chat_box.configure(state="disabled")
        for w in self._recs_scroll.winfo_children():
            w.destroy()
        self.on_show()

    # ── recommendations ───────────────────────────────────────────────────────

    def _refresh_recs(self, mods: list[dict]):
        for w in self._recs_scroll.winfo_children():
            w.destroy()
        for i, mod in enumerate(mods):
            self._make_rec_card(i, mod)

    def _make_rec_card(self, idx: int, mod: dict):
        SRC = {"modrinth": "#1BD96A", "curseforge": "#F16436", "spiget": "#1E88E5"}
        src = mod.get("source", "modrinth")

        card = ctk.CTkFrame(self._recs_scroll, corner_radius=6, height=50)
        card.pack(fill="x", pady=2)
        card.columnconfigure(0, weight=1)
        card.grid_propagate(False)

        ctk.CTkLabel(card, text=mod["name"],
                     font=ctk.CTkFont(size=11, weight="bold"),
                     anchor="w", wraplength=160).grid(
            row=0, column=0, sticky="w", padx=8, pady=(6, 0))
        ctk.CTkLabel(card, text=src,
                     font=ctk.CTkFont(size=9),
                     text_color=SRC.get(src, "#888")).grid(
            row=1, column=0, sticky="w", padx=8)
        ctk.CTkButton(card, text="🔍", width=28, height=28,
                      fg_color="#2a2a2a", hover_color="#FF6B35",
                      command=lambda m=mod: self._search_mod(m)).grid(
            row=0, column=1, rowspan=2, padx=(0, 6))

    def _search_mod(self, mod: dict):
        """Otwiera przeglądarkę z wyszukiwaniem moda."""
        if self._on_search_mod:
            self._on_search_mod(mod)
        else:
            self._navigate("browser")

    def _download_all_recs(self):
        """Otwiera przeglądarkę dla pierwszego moda z listy."""
        if self._extracted_mods:
            self._search_mod(self._extracted_mods[0])
