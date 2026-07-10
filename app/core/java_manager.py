"""
Wykrywanie instalacji Javy w systemie.
"""
import os
import shutil
import subprocess
from pathlib import Path


def find_java_executables() -> list[str]:
    """Zwraca listę znalezionych ścieżek do java.exe."""
    found: list[str] = []

    def _add(p: Path):
        s = str(p)
        if p.exists() and s not in found:
            found.append(s)

    # 1. JAVA_HOME
    jh = os.environ.get("JAVA_HOME", "")
    if jh:
        _add(Path(jh) / "bin" / "java.exe")

    # 2. PATH
    in_path = shutil.which("java")
    if in_path:
        _add(Path(in_path))

    # 3. Typowe lokalizacje Windows
    search_roots = [
        Path("C:/Program Files/Java"),
        Path("C:/Program Files/Eclipse Adoptium"),
        Path("C:/Program Files/Microsoft"),
        Path("C:/Program Files/BellSoft"),
        Path("C:/Program Files/Zulu"),
        Path("C:/Program Files/OpenJDK"),
        Path("C:/Program Files (x86)/Java"),
    ]
    for root in search_roots:
        if root.exists():
            try:
                for jdir in sorted(root.iterdir(), reverse=True):
                    _add(jdir / "bin" / "java.exe")
            except PermissionError:
                pass

    # 4. Minecraft's bundled JRE (C:/Users/<user>/AppData/Roaming/.minecraft/runtime)
    mc_runtime = Path(os.environ.get("APPDATA", "")) / ".minecraft" / "runtime"
    if mc_runtime.exists():
        for comp_dir in mc_runtime.iterdir():
            if not comp_dir.is_dir():
                continue
            for os_dir in comp_dir.iterdir():
                if not os_dir.is_dir():
                    continue
                for ver_dir in os_dir.iterdir():
                    _add(ver_dir / "bin" / "java.exe")

    return found


def get_java_version(java_path: str) -> str:
    """Zwraca string z wersją Javy lub 'Nieznana'."""
    try:
        r = subprocess.run(
            [java_path, "-version"],
            capture_output=True, text=True, timeout=5
        )
        output = (r.stderr or r.stdout).strip()
        first_line = output.splitlines()[0] if output else ""
        return first_line
    except Exception:
        return "Nieznana"


def get_java_major_version(java_path: str) -> int | None:
    """Zwraca główną wersję Javy (np. 17, 21) lub None."""
    ver_str = get_java_version(java_path)
    # "java version \"17.0.9\"" lub "openjdk version \"21.0.1\""
    import re
    m = re.search(r'"(\d+)(?:\.(\d+))?', ver_str)
    if m:
        major = int(m.group(1))
        if major == 1:  # Java 8 and below: "1.8.0_xxx"
            minor = m.group(2)
            return int(minor) if minor else 8
        return major
    return None


def find_best_java(min_version: int = 17) -> str | None:
    """Znajdź najlepszą Javę o wersji >= min_version."""
    candidates = find_java_executables()
    best: tuple[int, str] | None = None
    for path in candidates:
        ver = get_java_major_version(path)
        if ver is not None and ver >= min_version:
            if best is None or ver < best[0]:  # preferuj najniższą spełniającą wymagania
                best = (ver, path)
    return best[1] if best else (candidates[0] if candidates else None)
