import tkinter as tk
import customtkinter as ctk
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk

from ..api import modrinth, spiget


class ModDetailWindow(ctk.CTkToplevel):
    def __init__(self, parent, mod_data: dict, loader: str, game_version: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.mod_data = mod_data
        self.loader = loader
        self.game_version = game_version
        self.title(f"Moddy – {mod_data.get('name', 'Mod')}")
        self.geometry("700x580")
        self.resizable(True, True)
        self._build()
        self._load_full_description()

    def _build(self):
        # header
        header = ctk.CTkFrame(self, corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        self._icon_label = ctk.CTkLabel(header, text="")
        self._icon_label.pack(side="left", padx=12, pady=10)
        threading.Thread(target=self._load_icon, daemon=True).start()

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=8)
        ctk.CTkLabel(info, text=self.mod_data.get("name", ""), font=ctk.CTkFont(size=18, weight="bold"),
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=self.mod_data.get("description", "")[:140],
                     font=ctk.CTkFont(size=11), text_color="#aaa", anchor="w",
                     wraplength=480).pack(anchor="w")

        src = self.mod_data.get("source", "").upper()
        dl = self.mod_data.get("downloads", 0)
        ctk.CTkLabel(info, text=f"{src}  •  ⬇ {dl:,}",
                     font=ctk.CTkFont(size=10), text_color="#666", anchor="w").pack(anchor="w")

        # description area
        self._desc_box = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=12))
        self._desc_box.pack(fill="both", expand=True, padx=10, pady=(8, 4))
        self._desc_box.insert("1.0", "Ładowanie opisu...")
        self._desc_box.configure(state="disabled")

        # versions
        self._ver_frame = ctk.CTkScrollableFrame(self, height=100, label_text="Dostępne wersje")
        self._ver_frame.pack(fill="x", padx=10, pady=4)

    def _load_icon(self):
        url = self.mod_data.get("icon_url")
        if not url:
            return
        try:
            r = requests.get(url, timeout=5)
            img = Image.open(BytesIO(r.content)).convert("RGBA").resize((64, 64), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.after(0, lambda: self._icon_label.configure(image=photo, text=""))
            self._icon_photo = photo
        except Exception:
            pass

    def _load_full_description(self):
        threading.Thread(target=self._fetch_description, daemon=True).start()

    def _fetch_description(self):
        try:
            src = self.mod_data.get("source")
            desc = ""
            versions_info = []

            if src == "modrinth":
                project = modrinth.get_project(self.mod_data["id"])
                desc = project.get("body", project.get("description", ""))
                versions = modrinth.get_versions(self.mod_data["id"], self.loader, self.game_version)
                for v in versions[:8]:
                    versions_info.append(f"  {v.get('name', v.get('id', ''))}  —  {v.get('date_published', '')[:10]}")

            elif src == "spiget":
                resource = spiget.get_resource(self.mod_data["id"])
                desc_enc = resource.get("description", "")
                # spiget returns HTML-encoded description
                try:
                    import html
                    import re
                    desc = re.sub(r'<[^>]+>', '', html.unescape(desc_enc))
                except Exception:
                    desc = desc_enc
                vers = spiget.get_versions(self.mod_data["id"])
                for v in vers[:8]:
                    versions_info.append(f"  {v.get('name', v.get('id', ''))}")

            elif src == "curseforge":
                desc = self.mod_data.get("description", "Opis dostępny na CurseForge")
                cf = self.mod_data.get("cf_data", {})
                for lf in (cf.get("latestFilesIndexes") or [])[:8]:
                    versions_info.append(f"  {lf.get('filename', '')}  —  {lf.get('gameVersion', '')}")

            self.after(0, lambda: self._update_ui(desc, versions_info))
        except Exception as e:
            self.after(0, lambda: self._update_ui(f"Nie można załadować opisu: {e}", []))

    def _update_ui(self, desc: str, versions: list):
        self._desc_box.configure(state="normal")
        self._desc_box.delete("1.0", "end")
        self._desc_box.insert("1.0", desc)
        self._desc_box.configure(state="disabled")

        for child in self._ver_frame.winfo_children():
            child.destroy()
        if versions:
            for v in versions:
                ctk.CTkLabel(self._ver_frame, text=v, font=ctk.CTkFont(size=11),
                             text_color="#ccc", anchor="w").pack(anchor="w", fill="x")
        else:
            ctk.CTkLabel(self._ver_frame, text="  Brak danych o wersjach",
                         font=ctk.CTkFont(size=11), text_color="#666").pack(anchor="w")
