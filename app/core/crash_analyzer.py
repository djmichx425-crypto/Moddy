"""
Analizator crash reportów Minecraft z AI.
Czyta log/crash-report, wysyła do OpenRouter, zwraca diagnozę.
"""
from __future__ import annotations
import re
from pathlib import Path

from .minecraft_launcher import get_instance_dir, MINECRAFT_DIR

CRASH_PROMPT = """\
Jesteś ekspertem od Minecraft. Przeanalizuj poniższy crash report / log gry.

Twoja odpowiedź MUSI zawierać:
1. **Przyczyna kracha** (1-2 zdania)
2. **Winny mod lub komponent** (podaj dokładną nazwę i wersję jeśli widoczna)
3. **Rozwiązanie** (konkretne kroki, np. "Zaktualizuj Sodium do wersji X" lub "Usuń mod Y")

Bądź KONKRETNY. Jeśli widać conflict modów, napisz które.
Format: użyj nagłówków **Pogrubione** dla każdej sekcji.
Odpowiadaj po polsku.
"""


def find_crash_logs(installation: dict) -> list[Path]:
    """Znajdź pliki crash-report i logi dla instalacji."""
    inst_dir = get_instance_dir(installation)
    logs: list[Path] = []

    # crash-reports
    cr_dir = inst_dir / "crash-reports"
    if cr_dir.exists():
        logs.extend(sorted(cr_dir.glob("*.txt"), reverse=True)[:5])

    # logs/latest.log
    log_file = inst_dir / "logs" / "latest.log"
    if log_file.exists():
        logs.insert(0, log_file)

    return logs


def read_crash_log(path: Path, max_lines: int = 200) -> str:
    """Czyta i czyści log crashu."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        # Znajdź sekcję z błędem
        error_keywords = ["FATAL", "ERROR", "Exception", "Caused by",
                          "at net.minecraft", "crash-report"]
        relevant: list[str] = []
        in_stack = False

        for line in lines:
            if any(kw in line for kw in error_keywords):
                in_stack = True
            if in_stack:
                relevant.append(line)
            if len(relevant) >= max_lines:
                break

        if not relevant:
            relevant = lines[-max_lines:]

        return "\n".join(relevant)
    except Exception as e:
        return f"Błąd odczytu pliku: {e}"


def extract_mod_list(installation: dict) -> list[str]:
    """Wyciąga listę zainstalowanych modów z katalogu mods."""
    mods_dir = get_instance_dir(installation) / "mods"
    if not mods_dir.exists():
        return []
    return [f.stem for f in mods_dir.glob("*.jar")]


def analyze_crash(
    log_text: str,
    mod_list: list[str],
    api_key: str,
    stream_callback=None,
) -> str:
    """Analizuje crash używając AI. Zwraca pełną diagnozę."""
    from .ai_generator import stream_chat

    mods_info = "\n".join(f"- {m}" for m in mod_list[:50]) if mod_list else "(brak)"

    user_msg = (
        f"Zainstalowane mody:\n{mods_info}\n\n"
        f"--- LOG CRASHU ---\n{log_text[:3000]}\n--- KONIEC LOGU ---"
    )
    messages = [
        {"role": "system", "content": CRASH_PROMPT},
        {"role": "user",   "content": user_msg},
    ]

    result = ""
    for token in stream_chat(messages, api_key, on_token=stream_callback):
        result += token
    return result


def quick_scan_log(log_text: str) -> list[str]:
    """
    Szybkie lokalne skanowanie bez AI.
    Zwraca listę wykrytych problemów.
    """
    issues: list[str] = []

    patterns = [
        (r"OutOfMemoryError",
         "Brak pamięci RAM — zwiększ alokację w ustawieniach instalacji"),
        (r"java\.lang\.UnsatisfiedLinkError",
         "Brakujące natywne biblioteki — sprawdź wersję Javy"),
        (r"mixin.*incompatible|incompatible mixin",
         "Niekompatybilny Mixin — jeden z modów konflikuje z innymi"),
        (r"DuplicateModException|duplicate mod",
         "Zduplikowany mod — ten sam mod zainstalowany dwukrotnie"),
        (r"java\.lang\.ClassCastException.*mod",
         "Konflikt klas między modami"),
        (r"NullPointerException",
         "Błąd NullPointerException — prawdopodobnie niekompatybilne mody"),
        (r"failed to load.*mod|could not load mod",
         "Mod nie załadował się poprawnie"),
    ]

    for pattern, message in patterns:
        if re.search(pattern, log_text, re.IGNORECASE):
            issues.append(message)

    return list(dict.fromkeys(issues))   # deduplikacja
