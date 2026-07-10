"""
Generator paczek modów oparty na AI (OpenRouter / GPT-OSS-120B).
Strumieniuje odpowiedź token po tokenie i parsuje rekomendacje modów.
"""
from __future__ import annotations
import json
import re
import requests
from typing import Generator, Callable

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MODEL           = "google/gemma-4-31b-it:free"

SYSTEM_PROMPT = """\
Jesteś asystentem Moddy Launcher — eksperta od modów do Minecraft.
Pomagasz graczom dobierać mody pasujące do ich stylu gry i wersji Minecraft.

Zasady odpowiedzi:
- Odpowiadaj PO POLSKU, w przyjaznym tonie.
- Kiedy proponujesz mody, zawsze podaj ich dokładne nazwy w formacie:
  **Nazwa Moda** [modrinth] lub **Nazwa Moda** [curseforge]
- Krótko wyjaśnij do czego służy każdy mod (1-2 zdania).
- Jeśli pytanie jest ogólne, zapytaj o wersję MC i loader.
- Sugeruj 5–12 modów na zapytanie, nie więcej.
- Pamiętaj o modach zależnościach (np. Fabric API dla modów Fabric).
- Nie wymyślaj nazw modów — podawaj tylko istniejące.
"""


def stream_chat(
    messages: list[dict],
    api_key: str,
    on_token: Callable[[str], None] | None = None,
) -> Generator[str, None, None]:
    """
    Strumieniuje odpowiedź AI token po tokenie.
    Każdy yielded string to kawałek tekstu.
    """
    headers = {
        "Authorization":  f"Bearer {api_key}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "https://moddy-launcher.app",
        "X-Title":        "Moddy Launcher",
    }
    body = {
        "model":    MODEL,
        "messages": messages,
        "stream":   True,
        "max_tokens": 1500,
    }
    RETRY_CODES = {429, 500, 502, 503, 504}
    NO_RETRY_CODES = {400, 401, 403, 404, 422}
    MAX_RETRIES = 3
    last_err = ""

    for attempt in range(1, MAX_RETRIES + 1):
        last_err = ""
        try:
            r = requests.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=headers, json=body,
                stream=True, timeout=60)

            if r.status_code in NO_RETRY_CODES:
                last_err = f"HTTP {r.status_code}"
                break
            if r.status_code in RETRY_CODES:
                last_err = f"HTTP {r.status_code}"
                if attempt < MAX_RETRIES:
                    import time
                    time.sleep(2 * attempt)
                    continue
                break

            r.raise_for_status()

            for line in r.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                try:
                    chunk   = json.loads(data)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        if on_token:
                            on_token(content)
                        yield content
                except Exception:
                    continue
            return   # sukces

        except requests.exceptions.Timeout:
            last_err = "Timeout (brak odpowiedzi w 60 s)"
            if attempt < MAX_RETRIES:
                continue
        except requests.exceptions.ConnectionError:
            last_err = "Brak połączenia z internetem"
            break
        except requests.exceptions.RequestException as e:
            last_err = str(e)
            break

    # Wszystkie próby nieudane
    code = last_err
    if "503" in code or "502" in code:
        msg = (f"⚠ Serwer OpenRouter jest chwilowo przeciążony ({code}).\n"
               f"Spróbuj ponownie za kilka sekund.")
    elif "429" in code:
        msg = "⚠ Przekroczono limit zapytań. Poczekaj chwilę i spróbuj ponownie."
    elif "404" in code:
        msg = ("⚠ Model niedostępny na OpenRouter (404).\n"
               "Sprawdź czy masz klucz API w Ustawieniach → OpenRouter Key.\n"
               f"Model: {MODEL}")
    elif "401" in code or "403" in code:
        msg = "⚠ Nieprawidłowy klucz API. Sprawdź ustawienia OpenRouter."
    elif "Timeout" in code:
        msg = "⚠ Odpowiedź AI trwała zbyt długo. Spróbuj ponownie."
    else:
        msg = f"⚠ Błąd: {code}"
    yield f"\n{msg}"


def extract_mod_names(text: str) -> list[dict]:
    """
    Wyciąga rekomendacje modów z tekstu AI.
    Wzorzec: **Nazwa Moda** [modrinth] lub **Nazwa Moda** [curseforge]
    Zwraca: [{"name": "...", "source": "modrinth"/"curseforge"}, ...]
    """
    pattern = r'\*\*([^\*]+)\*\*\s*\[?(modrinth|curseforge|spiget)?\]?'
    mods = []
    seen = set()
    for m in re.finditer(pattern, text, re.IGNORECASE):
        name   = m.group(1).strip()
        source = (m.group(2) or "modrinth").lower()
        if name.lower() not in seen:
            seen.add(name.lower())
            mods.append({"name": name, "source": source})
    return mods


def build_messages(history: list[dict], user_msg: str,
                   loader: str = "", mc_version: str = "") -> list[dict]:
    """Buduje listę wiadomości dla API."""
    context = ""
    if loader and mc_version:
        context = (f"\n\n[Kontekst: gracz używa {loader.capitalize()} "
                   f"dla Minecraft {mc_version}]")

    msgs = [{"role": "system", "content": SYSTEM_PROMPT + context}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": user_msg})
    return msgs
