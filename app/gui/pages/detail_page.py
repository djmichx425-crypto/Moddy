import re
import html as html_module
import customtkinter as ctk
import threading
import requests
from io import BytesIO
from PIL import Image

from ...api import modrinth, spiget
from ...auth.token_store import is_premium
from ...core.compatibility_checker import CompatResult, STATUS_OK, STATUS_WARN, STATUS_ERROR

FREE_DESC_LIMIT = 500


def _clean_description(text: str) -> str:
    """Usuń tagi HTML i markdown, zostaw czytelny tekst."""
    # decode HTML entities
    text = html_module.unescape(text)
    # usuń bloki kodu
    text = re.sub(r'```[\s\S]*?```', '[kod]', text)
    text = re.sub(r'`[^`]+`', lambda m: m.group().strip('`'), text)
    # usuń obrazki ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # zamień linki [tekst](url) na sam tekst
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # usuń znaczniki HTML
    text = re.sub(r'<[^>]+>', '', text)
    # zamień nagłówki ### na DUŻE LITERY
    text = re.sub(r'^#{1,6}\s*(.+)', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    # usuń bold/italic
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # usuń poziome linie
    text = re.sub(r'^[-*_]{3,}$', '─' * 40, text, flags=re.MULTILINE)
    # usuń nadmiarowe puste linie
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class DetailPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._user_info: dict | None = None
        self._compat_result: CompatResult | None = None
        self._build()

    def set_user(self, user_info: dict | None):
        self._user_info = user_info

    def _build(self):
        # header
        self._header = ctk.CTkFrame(self, fg_color="#222222", corner_radius=0, height=90)
        self._header.pack(fill="x")
        self._header.pack_propagate(False)

        self._icon_label = ctk.CTkLabel(self._header, text="")
        self._icon_label.pack(side="left", padx=12, pady=10)

        info_frame = ctk.CTkFrame(self._header, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=8)

        self._name_label = ctk.CTkLabel(info_frame, text="",
                                         font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
        self._name_label.pack(anchor="w")

        self._desc_label = ctk.CTkLabel(info_frame, text="",
                                         font=ctk.CTkFont(size=11), text_color="#aaa",
                                         anchor="w", wraplength=520, justify="left")
        self._desc_label.pack(anchor="w")

        self._meta_label = ctk.CTkLabel(info_frame, text="",
                                         font=ctk.CTkFont(size=10), text_color="#666", anchor="w")
        self._meta_label.pack(anchor="w")

        # full description
        self._body = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=12))
        self._body.pack(fill="both", expand=True, padx=10, pady=(8, 4))
        self._body.configure(state="disabled")

        # compat panel
        self._compat_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=8)
        self._compat_frame.pack(fill="x", padx=10, pady=(0, 4))

        # versions
        self._ver_frame = ctk.CTkScrollableFrame(self, height=90, label_text="Dostępne wersje",
                                                  fg_color="transparent")
        self._ver_frame.pack(fill="x", padx=10, pady=(0, 8))

    def on_show(self, mod_data: dict = None,
                compat_result: CompatResult | None = None, **_):
        if not mod_data:
            return
        self._mod_data = mod_data
        self._compat_result = compat_result
        self._icon_label.configure(image="", text="")
        self._render_compat(compat_result)

        self._name_label.configure(text=mod_data.get("name", ""))
        self._desc_label.configure(text=mod_data.get("description", "")[:160])
        src = mod_data.get("source", "").upper()
        dl = mod_data.get("downloads", 0)
        self._meta_label.configure(text=f"{src}  •  ⬇ {dl:,}")

        self._body.configure(state="normal")
        self._body.delete("1.0", "end")
        self._body.insert("1.0", "Ładowanie opisu...")
        self._body.configure(state="disabled")

        for w in self._ver_frame.winfo_children():
            w.destroy()

        threading.Thread(target=self._load_icon, daemon=True).start()
        threading.Thread(target=self._load_description, daemon=True).start()

    def _render_compat(self, result: CompatResult | None):
        """Renderuje panel kompatybilności pod opisem."""
        for w in self._compat_frame.winfo_children():
            w.destroy()

        if result is None:
            self._compat_frame.pack_forget()
            return

        self._compat_frame.pack(fill="x", padx=10, pady=(0, 4))

        top_row = ctk.CTkFrame(self._compat_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(top_row, text="🔍  Kompatybilność",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkLabel(top_row, text=result.short_label(),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=result.color()).pack(side="left", padx=12)

        if result.message:
            ctk.CTkLabel(self._compat_frame, text=result.message,
                         font=ctk.CTkFont(size=11), text_color="#888",
                         anchor="w").pack(fill="x", padx=12, pady=(0, 4))

        # Zależności
        all_deps = result.deps
        if not all_deps:
            if result.status == STATUS_OK:
                ctk.CTkLabel(self._compat_frame,
                             text="Brak wymaganych zależności.",
                             font=ctk.CTkFont(size=10), text_color="#555").pack(
                    anchor="w", padx=12, pady=(0, 8))
            return

        dep_frame = ctk.CTkFrame(self._compat_frame, fg_color="transparent")
        dep_frame.pack(fill="x", padx=12, pady=(0, 8))

        for dep in all_deps:
            if dep.dep_type == "embedded":
                continue
            icons = {
                "required":             ("⚙", "#FF8C00" if not dep.present else "#4CAF50"),
                "optional":             ("○", "#888" if not dep.present else "#4CAF50"),
                "incompatible":         ("✗", "#FF4444" if dep.present else "#555"),
                "required_unavailable": ("✗", "#FF4444"),
            }
            icon, color = icons.get(dep.dep_type, ("?", "#666"))
            status = "✓" if dep.present else ("BRAK" if "required" in dep.dep_type else "opcj.")
            label = f"{icon} {dep.name or dep.project_id}  [{status}]"

            ctk.CTkLabel(dep_frame, text=label,
                         font=ctk.CTkFont(size=10), text_color=color,
                         anchor="w").pack(anchor="w", pady=1)

    def _load_icon(self):
        url = self._mod_data.get("icon_url")
        if not url:
            return
        try:
            r = requests.get(url, timeout=5)
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 64))
            self.after(0, lambda: self._icon_label.configure(image=ctk_img, text=""))
            self._ctk_icon = ctk_img  # keep reference
        except Exception:
            pass

    def _load_description(self):
        try:
            src = self._mod_data.get("source")
            desc, versions_text = "", []

            if src == "modrinth":
                project = modrinth.get_project(self._mod_data["id"])
                desc = _clean_description(project.get("body", project.get("description", "")))
                versions = modrinth.get_versions(self._mod_data["id"])
                for v in versions[:8]:
                    versions_text.append(f"  {v.get('name', v.get('id', ''))}  —  {v.get('date_published', '')[:10]}")

            elif src == "spiget":
                resource = spiget.get_resource(self._mod_data["id"])
                desc = _clean_description(resource.get("description", ""))
                for v in spiget.get_versions(self._mod_data["id"])[:8]:
                    versions_text.append(f"  {v.get('name', v.get('id', ''))}")

            elif src == "curseforge":
                desc = self._mod_data.get("description", "Opis dostępny na stronie CurseForge.")
                for lf in (self._mod_data.get("cf_data", {}).get("latestFilesIndexes") or [])[:8]:
                    versions_text.append(f"  {lf.get('filename', '')}  ({lf.get('gameVersion', '')})")

            self.after(0, lambda: self._update_ui(desc, versions_text))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._update_ui(f"Nie można załadować opisu: {m}", []))

    def _update_ui(self, desc: str, versions: list):
        self._body.configure(state="normal")
        self._body.delete("1.0", "end")
        if not is_premium(self._user_info) and len(desc) > FREE_DESC_LIMIT:
            preview = desc[:FREE_DESC_LIMIT]
            self._body.insert("1.0", preview)
            self._body.insert("end", f"\n\n{'─'*40}\n✨ Zaloguj się jako Premium aby zobaczyć pełny opis ({len(desc)} znaków)\n{'─'*40}")
        else:
            self._body.insert("1.0", desc)
        self._body.configure(state="disabled")

        for w in self._ver_frame.winfo_children():
            w.destroy()
        items = versions or ["  Brak danych o wersjach"]
        for v in items:
            ctk.CTkLabel(self._ver_frame, text=v,
                         font=ctk.CTkFont(size=11), text_color="#ccc", anchor="w").pack(
                anchor="w", fill="x")
