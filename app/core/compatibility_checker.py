"""
Sprawdzanie kompatybilności modów.

Co jest sprawdzane:
  1. Wersja MC + loader — czy istnieje plik moda dla danej kombinacji
  2. Wymagane zależności — jakie inne mody muszą być zainstalowane
  3. Opcjonalne zależności — co polepsza działanie
  4. Konflikty — co NIE może być zainstalowane razem

Źródła:
  - Modrinth  (pełna informacja o zależnościach)
  - CurseForge (tylko filtrowanie wersji, brak zależności w API)
  - Spiget    (brak metadanych zależności)
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable

import requests

BASE_MR = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "moddy-launcher/2.0"}


# ── typy wyników ──────────────────────────────────────────────────────────────

STATUS_OK      = "ok"       # pełna kompatybilność
STATUS_WARN    = "warn"     # kompatybilny, ale brakuje opcjonalnych zależności
STATUS_ERROR   = "error"    # niezgodny (brak pliku lub wymagana zależność)
STATUS_UNKNOWN = "unknown"  # nie można sprawdzić (np. Spiget)


@dataclass
class Dependency:
    project_id: str
    name: str           # "" jeśli nieznana
    dep_type: str       # "required" | "optional" | "incompatible" | "embedded"
    present: bool       # czy jest w bibliotece lub already installed


@dataclass
class CompatResult:
    mod_id:    str
    mod_name:  str
    source:    str
    status:    str = STATUS_UNKNOWN
    message:   str = ""
    deps:      list[Dependency] = field(default_factory=list)

    @property
    def missing_required(self) -> list[Dependency]:
        return [d for d in self.deps
                if d.dep_type == "required" and not d.present]

    @property
    def missing_optional(self) -> list[Dependency]:
        return [d for d in self.deps
                if d.dep_type == "optional" and not d.present]

    @property
    def conflicts(self) -> list[Dependency]:
        return [d for d in self.deps
                if d.dep_type == "incompatible" and d.present]

    def short_label(self) -> str:
        if self.status == STATUS_OK:
            return "✅  Kompatybilny"
        if self.status == STATUS_WARN:
            n = len(self.missing_optional)
            return f"⚠  Brak {n} opt. zależności"
        if self.status == STATUS_ERROR:
            if self.missing_required:
                names = ", ".join(d.name or d.project_id
                                  for d in self.missing_required[:2])
                return f"❌  Brakuje: {names}"
            if self.conflicts:
                names = ", ".join(d.name or d.project_id
                                  for d in self.conflicts[:1])
                return f"❌  Konflikt: {names}"
            return f"❌  {self.message or 'Niezgodny'}"
        return "❓  Brak danych"

    def color(self) -> str:
        return {
            STATUS_OK:      "#4CAF50",
            STATUS_WARN:    "#FF8C00",
            STATUS_ERROR:   "#FF4444",
            STATUS_UNKNOWN: "#666666",
        }[self.status]


# ── główna funkcja sprawdzająca ───────────────────────────────────────────────

def check_mod(
    mod_id: str,
    mod_name: str,
    source: str,
    loader: str,
    mc_version: str,
    settings: dict,
    library_mod_ids: set[str] | None = None,
) -> CompatResult:
    """
    Sprawdza kompatybilność jednego moda z daną instalacją.
    library_mod_ids – zbiór mod_id już posiadanych modów (do sprawdzenia zależności).
    """
    result = CompatResult(mod_id=mod_id, mod_name=mod_name, source=source)
    known_ids = library_mod_ids or set()

    if source == "modrinth":
        _check_modrinth(result, loader, mc_version, known_ids)
    elif source == "curseforge":
        _check_curseforge(result, loader, mc_version, settings)
    elif source == "spiget":
        result.status = STATUS_UNKNOWN
        result.message = "Spiget nie udostępnia metadanych kompatybilności"
    else:
        result.status = STATUS_UNKNOWN

    return result


def check_mod_async(
    mod_id: str,
    mod_name: str,
    source: str,
    loader: str,
    mc_version: str,
    settings: dict,
    library_mod_ids: set[str] | None,
    callback: Callable[[CompatResult], None],
) -> None:
    """Sprawdza kompatybilność w tle i woła callback z wynikiem."""
    def _run():
        result = check_mod(mod_id, mod_name, source, loader, mc_version,
                           settings, library_mod_ids)
        callback(result)
    threading.Thread(target=_run, daemon=True).start()


def check_library(
    installation: dict,
    library_mods: list[dict],
    settings: dict,
) -> list[CompatResult]:
    """Sprawdza wszystkie mody z biblioteki dla danej instalacji."""
    loader     = installation.get("loader", "")
    mc_version = installation.get("version") or installation.get("game_version", "")
    known_ids  = {str(m.get("mod_id", "")) for m in library_mods}

    results: list[CompatResult] = []
    for mod in library_mods:
        r = check_mod(
            mod_id=str(mod.get("mod_id", "")),
            mod_name=mod.get("name", mod.get("filename", "?")),
            source=mod.get("source", ""),
            loader=loader,
            mc_version=mc_version,
            settings=settings,
            library_mod_ids=known_ids,
        )
        results.append(r)
    return results


# ── Modrinth ──────────────────────────────────────────────────────────────────

def _check_modrinth(
    result: CompatResult,
    loader: str,
    mc_version: str,
    known_ids: set[str],
):
    try:
        versions = _mr_get_versions(result.mod_id, loader, mc_version)
    except Exception as e:
        result.status  = STATUS_UNKNOWN
        result.message = f"Błąd API: {e}"
        return

    if not versions:
        # Spróbuj bez filtrowania wersji — może mod istnieje dla innego loadera
        try:
            any_versions = _mr_get_versions(result.mod_id)
        except Exception:
            any_versions = []

        if any_versions:
            supported = sorted({
                v for ver in any_versions
                for v in ver.get("game_versions", [])
            }, reverse=True)
            loaders = sorted({
                ldr for ver in any_versions
                for ldr in ver.get("loaders", [])
            })
            result.status  = STATUS_ERROR
            result.message = (
                f"Brak pliku dla {loader} {mc_version}. "
                f"Wspiera: {', '.join(loaders)} / "
                f"{', '.join(supported[:5])}"
            )
        else:
            result.status  = STATUS_ERROR
            result.message = "Mod nie ma żadnych plików"
        return

    # Jest wersja — sprawdź zależności
    ver_data  = versions[0]
    raw_deps  = ver_data.get("dependencies", [])
    result.deps = _resolve_deps(raw_deps, loader, mc_version, known_ids)

    missing_req = result.missing_required
    conflicts   = result.conflicts

    if conflicts:
        names = ", ".join(d.name or d.project_id for d in conflicts[:2])
        result.status  = STATUS_ERROR
        result.message = f"Konflikt z: {names}"
    elif missing_req:
        names = ", ".join(d.name or d.project_id for d in missing_req[:3])
        result.status  = STATUS_ERROR
        result.message = f"Wymagane zależności: {names}"
    elif result.missing_optional:
        result.status  = STATUS_WARN
        result.message = "Brakuje opcjonalnych zależności"
    else:
        result.status  = STATUS_OK
        result.message = f"Kompatybilny z {loader} {mc_version}"


def _mr_get_versions(project_id: str, loader: str = "", mc_version: str = "") -> list:
    params: dict = {}
    if loader:
        import json as _json
        params["loaders"] = _json.dumps([loader.lower()])
    if mc_version:
        import json as _json
        params["game_versions"] = _json.dumps([mc_version])
    r = requests.get(f"{BASE_MR}/project/{project_id}/version",
                     params=params, headers=HEADERS, timeout=8)
    r.raise_for_status()
    return r.json()


def _resolve_deps(
    raw_deps: list[dict],
    loader: str,
    mc_version: str,
    known_ids: set[str],
) -> list[Dependency]:
    """Pobiera nazwy projektów dla zależności i sprawdza czy są w bibliotece."""
    deps: list[Dependency] = []
    for d in raw_deps:
        dep_type   = d.get("dependency_type", "required")
        project_id = d.get("project_id") or ""
        if not project_id or dep_type == "embedded":
            continue

        # Pobierz nazwę projektu
        name = _get_project_name(project_id)
        present = project_id in known_ids

        # Dla "required" sprawdź też czy zależność jest dostępna dla tej wersji
        if dep_type == "required" and not present:
            try:
                dep_versions = _mr_get_versions(project_id, loader, mc_version)
                available = bool(dep_versions)
            except Exception:
                available = True   # nie wiemy, nie blokuj
            if not available:
                dep_type = "required_unavailable"

        deps.append(Dependency(
            project_id=project_id,
            name=name,
            dep_type=dep_type,
            present=present,
        ))
    return deps


def _get_project_name(project_id: str) -> str:
    try:
        r = requests.get(f"{BASE_MR}/project/{project_id}",
                         headers=HEADERS, timeout=6)
        if r.ok:
            return r.json().get("title", project_id)
    except Exception:
        pass
    return project_id


# ── CurseForge ────────────────────────────────────────────────────────────────

def _check_curseforge(
    result: CompatResult,
    loader: str,
    mc_version: str,
    settings: dict,
):
    key = settings.get("curseforge_api_key", "")
    if not key:
        result.status  = STATUS_UNKNOWN
        result.message = "Brak klucza CurseForge API"
        return
    try:
        from ..api import curseforge as cf
        files = cf.get_files(key, result.mod_id, mc_version)
        if files:
            result.status  = STATUS_OK
            result.message = f"Dostępny dla Minecraft {mc_version}"
        else:
            result.status  = STATUS_ERROR
            result.message = f"Brak pliku dla Minecraft {mc_version}"
    except Exception as e:
        result.status  = STATUS_UNKNOWN
        result.message = f"Błąd CurseForge: {e}"
