import tkinter as tk
import customtkinter as ctk
import threading

from ...auth.api_client import register, login, server_online
from ...auth.token_store import save_session


class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, on_logged_in, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#111111", **kwargs)
        self._navigate = navigate
        self._on_logged_in = on_logged_in
        self._build()

    def _build(self):
        # centralny card
        card = ctk.CTkFrame(self, corner_radius=20, fg_color="#1e1e1e",
                             border_width=1, border_color="#333")
        card.place(relx=0.5, rely=0.5, anchor="center")

        # logo
        ctk.CTkLabel(card, text="moddy",
                     font=ctk.CTkFont(size=40, weight="bold"),
                     text_color="#FF6B35").pack(pady=(32, 2))
        ctk.CTkLabel(card, text="Minecraft Mod Manager",
                     font=ctk.CTkFont(size=12), text_color="#555").pack(pady=(0, 20))

        # premium info
        badge = ctk.CTkFrame(card, fg_color="#1a1a0a", corner_radius=8)
        badge.pack(padx=36, fill="x", pady=(0, 16))
        ctk.CTkLabel(badge, text="✨  Moddy Premium",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#FFD700").pack(pady=(8, 2))
        ctk.CTkLabel(badge, text="Zaloguj się aby odblokować pełne opisy\ni nieograniczoną liczbę wyników",
                     font=ctk.CTkFont(size=10), text_color="#888",
                     justify="center").pack(pady=(0, 8))

        # status serwera
        self._server_lbl = ctk.CTkLabel(card, text="Sprawdzanie serwera...",
                                         font=ctk.CTkFont(size=10), text_color="#555")
        self._server_lbl.pack()

        # zakładki
        self._tab = ctk.CTkTabview(card, width=360, height=280,
                                    fg_color="#1e1e1e", segmented_button_fg_color="#2a2a2a",
                                    segmented_button_selected_color="#FF6B35",
                                    segmented_button_selected_hover_color="#e05520")
        self._tab.pack(padx=24, pady=8)
        self._tab.add("Zaloguj się")
        self._tab.add("Zarejestruj się")

        self._build_login_tab()
        self._build_register_tab()

        # kontynuuj bez logowania
        ctk.CTkButton(card, text="Kontynuuj bez logowania  →",
                      font=ctk.CTkFont(size=11), height=32,
                      fg_color="transparent", hover_color="#2a2a2a",
                      text_color="#666",
                      command=lambda: self._on_logged_in(None, None)).pack(pady=(0, 24))

        threading.Thread(target=self._check_server, daemon=True).start()

    def _build_login_tab(self):
        tab = self._tab.tab("Zaloguj się")

        ctk.CTkLabel(tab, text="E-mail:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(8, 2))
        self._login_email = ctk.CTkEntry(tab, placeholder_text="adres@email.com", height=34)
        self._login_email.pack(fill="x", padx=4)

        ctk.CTkLabel(tab, text="Hasło:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(8, 2))
        self._login_pass = ctk.CTkEntry(tab, placeholder_text="••••••••", show="•", height=34)
        self._login_pass.pack(fill="x", padx=4)
        self._login_pass.bind("<Return>", lambda _: self._do_login())

        self._login_err = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=10),
                                        text_color="#FF4444", wraplength=320)
        self._login_err.pack(pady=(4, 0))

        self._login_btn = ctk.CTkButton(tab, text="Zaloguj się", height=36,
                                         fg_color="#FF6B35", hover_color="#e05520",
                                         command=self._do_login)
        self._login_btn.pack(fill="x", padx=4, pady=(6, 4))

    def _build_register_tab(self):
        tab = self._tab.tab("Zarejestruj się")

        ctk.CTkLabel(tab, text="Nazwa użytkownika:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(6, 2))
        self._reg_user = ctk.CTkEntry(tab, placeholder_text="MojaNazwa", height=32)
        self._reg_user.pack(fill="x", padx=4)

        ctk.CTkLabel(tab, text="E-mail:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(6, 2))
        self._reg_email = ctk.CTkEntry(tab, placeholder_text="adres@email.com", height=32)
        self._reg_email.pack(fill="x", padx=4)

        ctk.CTkLabel(tab, text="Hasło (min. 6 znaków):", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", padx=4, pady=(6, 2))
        self._reg_pass = ctk.CTkEntry(tab, placeholder_text="••••••••", show="•", height=32)
        self._reg_pass.pack(fill="x", padx=4)
        self._reg_pass.bind("<Return>", lambda _: self._do_register())

        self._reg_err = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=10),
                                      text_color="#FF4444", wraplength=320)
        self._reg_err.pack(pady=(2, 0))

        self._reg_btn = ctk.CTkButton(tab, text="Utwórz konto", height=34,
                                       fg_color="#FF6B35", hover_color="#e05520",
                                       command=self._do_register)
        self._reg_btn.pack(fill="x", padx=4, pady=(4, 4))

    # ── server check ──────────────────────────────────────────────────────────

    def _check_server(self):
        online = server_online()
        if online:
            self.after(0, lambda: self._server_lbl.configure(
                text="✅ Serwer online", text_color="#4CAF50"))
        else:
            self.after(0, lambda: self._server_lbl.configure(
                text="⚠ Serwer offline — uruchom serwer aby się zalogować",
                text_color="#FF6B35"))
            self.after(0, lambda: self._login_btn.configure(state="disabled"))
            self.after(0, lambda: self._reg_btn.configure(state="disabled"))

    def on_show(self, **_):
        self._login_err.configure(text="")
        self._reg_err.configure(text="")
        threading.Thread(target=self._check_server, daemon=True).start()

    # ── login ─────────────────────────────────────────────────────────────────

    def _do_login(self):
        email = self._login_email.get().strip()
        password = self._login_pass.get()
        if not email or not password:
            self._login_err.configure(text="Wypełnij wszystkie pola")
            return
        self._login_btn.configure(state="disabled", text="Logowanie...")
        threading.Thread(target=self._login_thread, args=(email, password), daemon=True).start()

    def _login_thread(self, email: str, password: str):
        try:
            data = login(email, password)
            save_session(data["access_token"], data["user"])
            self.after(0, lambda: self._on_logged_in(data["access_token"], data["user"]))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._login_err.configure(text=m))
            self.after(0, lambda: self._login_btn.configure(state="normal", text="Zaloguj się"))

    # ── register ──────────────────────────────────────────────────────────────

    def _do_register(self):
        username = self._reg_user.get().strip()
        email    = self._reg_email.get().strip()
        password = self._reg_pass.get()
        if not username or not email or not password:
            self._reg_err.configure(text="Wypełnij wszystkie pola")
            return
        self._reg_btn.configure(state="disabled", text="Tworzenie konta...")
        threading.Thread(target=self._register_thread,
                         args=(username, email, password), daemon=True).start()

    def _register_thread(self, username: str, email: str, password: str):
        try:
            data = register(username, email, password)
            save_session(data["access_token"], data["user"])
            self.after(0, lambda: self._on_logged_in(data["access_token"], data["user"]))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._reg_err.configure(text=m))
            self.after(0, lambda: self._reg_btn.configure(state="normal", text="Utwórz konto"))
