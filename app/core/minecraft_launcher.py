"""
Główny moduł launchera Minecraft.
Obsługuje: instalację wersji, instalację loaderów, uruchamianie gry.
Używa biblioteki minecraft-launcher-lib.
"""
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable

APPDATA = Path(os.environ.get("APPDATA", "~"))

# Katalog z plikami gry (assets, biblioteki, wersje) – współdzielony
MINECRAFT_DIR = APPDATA / "moddy" / ".minecraft"
# Katalog instancji (osobny dla każdej instalacji)
INSTANCES_DIR = APPDATA / "moddy" / "instances"


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "default"


def get_instance_dir(installation: dict) -> Path:
    return INSTANCES_DIR / _safe_name(installation.get("name", "default"))


def get_mods_dir(installation: dict) -> Path:
    return get_instance_dir(installation) / "mods"


def ensure_instance(installation: dict):
    d = get_instance_dir(installation)
    for sub in ("mods", "saves", "config", "resourcepacks", "shaderpacks"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    MINECRAFT_DIR.mkdir(parents=True, exist_ok=True)


# ── version lists ─────────────────────────────────────────────────────────────

def get_version_list(include_snapshots: bool = False) -> list[dict]:
    """
    Zwraca listę dostępnych wersji Minecraft.
    Każdy element: {"id": "1.21.1", "type": "release", "releaseTime": "..."}
    """
    try:
        import minecraft_launcher_lib as mll
        versions = mll.utils.get_version_list()
        if not include_snapshots:
            versions = [v for v in versions if v["type"] == "release"]
        return versions
    except Exception:
        # Fallback: popularne wersje
        return [{"id": v, "type": "release"} for v in [
            "1.21.5", "1.21.4", "1.21.1", "1.21",
            "1.20.6", "1.20.4", "1.20.2", "1.20.1", "1.20",
            "1.19.4", "1.19.2", "1.18.2", "1.17.1", "1.16.5", "1.12.2", "1.8.9",
        ]]


def get_fabric_loader_versions() -> list[str]:
    try:
        import minecraft_launcher_lib as mll
        loaders = mll.fabric.get_all_loader()
        return [ldr["version"] for ldr in loaders]
    except Exception:
        return []


def get_forge_version(mc_version: str) -> str | None:
    try:
        import minecraft_launcher_lib as mll
        return mll.forge.find_forge_version(mc_version)
    except Exception:
        return None


def get_quilt_loader_versions() -> list[str]:
    try:
        import minecraft_launcher_lib as mll
        loaders = mll.quilt.get_all_loader()
        return [ldr["version"] for ldr in loaders]
    except Exception:
        return []


def get_neoforge_latest(mc_version: str) -> str | None:
    try:
        import minecraft_launcher_lib as mll
        if not hasattr(mll, "neoforge"):
            return None
        versions = mll.neoforge.get_neoforge_versions()
        mc_short = mc_version.lstrip("1.")
        for v in versions:
            if v.startswith(mc_short):
                return v
    except Exception:
        pass
    return None


# ── installation ──────────────────────────────────────────────────────────────

CallbackDict = dict  # {"setStatus": callable, "setProgress": callable, "setMax": callable}


def install_version(installation: dict,
                    callback: CallbackDict | None = None,
                    java: str | None = None):
    """
    Pobiera i instaluje Minecraft + mod loader dla danej instalacji.
    Rzuca RuntimeError w razie błędu.
    """
    try:
        import minecraft_launcher_lib as mll
    except ImportError:
        raise RuntimeError("Brak biblioteki minecraft-launcher-lib!\n"
                           "Zainstaluj: pip install minecraft-launcher-lib")

    mc_version: str = installation.get("version") or installation.get("game_version", "1.21.1")
    loader: str = installation.get("loader", "vanilla").lower()
    loader_ver: str | None = installation.get("loader_version")
    java = java or installation.get("java_path") or None

    ensure_instance(installation)
    cb = callback or {}

    # ── 1. Vanilla ────────────────────────────────────────────────────────────
    _status(cb, f"Pobieranie Minecraft {mc_version}…")
    try:
        mll.install.install_minecraft_version(
            mc_version, str(MINECRAFT_DIR), callback=cb
        )
    except Exception as e:
        raise RuntimeError(f"Błąd instalacji Minecraft {mc_version}: {e}")

    # ── 2. Mod loader ─────────────────────────────────────────────────────────
    if loader == "fabric":
        _status(cb, "Instalowanie Fabric…")
        try:
            mll.fabric.install_fabric(
                mc_version, str(MINECRAFT_DIR),
                loader_version=loader_ver or None,
                callback=cb, java=java,
            )
        except Exception as e:
            raise RuntimeError(f"Błąd instalacji Fabric: {e}")

    elif loader == "forge":
        forge_id = loader_ver or get_forge_version(mc_version)
        if forge_id:
            _status(cb, f"Instalowanie Forge {forge_id}…")
            try:
                mll.forge.install_forge_version(
                    forge_id, str(MINECRAFT_DIR), callback=cb, java=java
                )
            except Exception as e:
                raise RuntimeError(f"Błąd instalacji Forge: {e}")
        else:
            raise RuntimeError(f"Nie znaleziono Forge dla Minecraft {mc_version}")

    elif loader == "quilt":
        _status(cb, "Instalowanie Quilt…")
        try:
            mll.quilt.install_quilt(
                mc_version, str(MINECRAFT_DIR),
                loader_version=loader_ver or None,
                callback=cb,
            )
        except Exception as e:
            raise RuntimeError(f"Błąd instalacji Quilt: {e}")

    elif loader == "neoforge":
        if not hasattr(mll, "neoforge"):
            raise RuntimeError("NeoForge nie jest obsługiwany w tej wersji biblioteki.\n"
                               "Użyj Fabric lub Forge.")
        nf_ver = loader_ver or get_neoforge_latest(mc_version)
        if nf_ver:
            _status(cb, f"Instalowanie NeoForge {nf_ver}…")
            try:
                mll.neoforge.install_neoforge_version(
                    nf_ver, str(MINECRAFT_DIR), callback=cb, java=java
                )
            except Exception as e:
                raise RuntimeError(f"Błąd instalacji NeoForge: {e}")
        else:
            raise RuntimeError(f"Nie znaleziono NeoForge dla Minecraft {mc_version}")

    # vanilla – już zainstalowane w kroku 1


def _status(cb: dict, msg: str):
    fn = cb.get("setStatus")
    if fn:
        fn(msg)


# ── detect installed version id ───────────────────────────────────────────────

def get_launch_version_id(installation: dict) -> str:
    """Zwraca ID wersji do uruchomienia (np. 'fabric-loader-0.16.0-1.21.1')."""
    mc_version = installation.get("version") or installation.get("game_version", "1.21.1")
    loader = installation.get("loader", "vanilla").lower()
    loader_ver = installation.get("loader_version")

    if loader == "vanilla":
        return mc_version

    versions_dir = MINECRAFT_DIR / "versions"

    if loader == "fabric":
        if loader_ver:
            return f"fabric-loader-{loader_ver}-{mc_version}"
        if versions_dir.exists():
            for d in versions_dir.iterdir():
                n = d.name
                if n.startswith("fabric-loader-") and n.endswith(f"-{mc_version}"):
                    return n
        return mc_version

    if loader == "forge":
        if loader_ver:
            return loader_ver
        if versions_dir.exists():
            for d in versions_dir.iterdir():
                n = d.name
                if "forge" in n.lower() and mc_version in n:
                    return n
        return mc_version

    if loader == "quilt":
        if loader_ver:
            return f"quilt-loader-{loader_ver}-{mc_version}"
        if versions_dir.exists():
            for d in versions_dir.iterdir():
                n = d.name
                if "quilt" in n.lower() and mc_version in n:
                    return n
        return mc_version

    if loader == "neoforge":
        if loader_ver:
            return f"neoforge-{loader_ver}"
        if versions_dir.exists():
            for d in versions_dir.iterdir():
                n = d.name
                if "neoforge" in n.lower():
                    return n
        return mc_version

    return mc_version


def is_installed(installation: dict) -> bool:
    """Sprawdza czy wersja jest zainstalowana lokalnie."""
    version_id = get_launch_version_id(installation)
    ver_json = MINECRAFT_DIR / "versions" / version_id / f"{version_id}.json"
    return ver_json.exists()


# ── launch ────────────────────────────────────────────────────────────────────

def launch(
    installation: dict,
    account: dict,
    on_start: Callable | None = None,
    on_stop: Callable | None = None,
    on_output: Callable[[str], None] | None = None,
) -> None:
    """
    Uruchamia Minecraft w osobnym wątku.
    on_start() – wywoływane przed startem
    on_stop()  – wywoływane po zamknięciu gry
    on_output(line) – linia z stdout/stderr gry
    """
    try:
        import minecraft_launcher_lib as mll
    except ImportError:
        raise RuntimeError("Brak biblioteki minecraft-launcher-lib!")

    version_id = get_launch_version_id(installation)
    instance_dir = get_instance_dir(installation)
    memory_mb = installation.get("memory_mb", 2048)
    java_path = installation.get("java_path") or None

    options: dict = {
        "username": account["username"],
        "uuid": account["uuid"],
        "token": account.get("token", "0"),
        "userType": "msa" if account.get("type") == "microsoft" else "offline",
        "jvmArguments": [
            f"-Xmx{memory_mb}M",
            "-Xms512M",
            "-XX:+UseG1GC",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:G1NewSizePercent=20",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
        ],
        "gameDirectory": str(instance_dir),
    }

    try:
        command = mll.command.get_minecraft_command(
            version=version_id,
            minecraft_directory=str(MINECRAFT_DIR),
            options=options,
        )
    except Exception as e:
        raise RuntimeError(f"Nie można przygotować polecenia uruchomienia: {e}")

    if java_path:
        command[0] = java_path

    def _run():
        if on_start:
            on_start()
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in proc.stdout:
                if on_output:
                    on_output(line.rstrip())
            proc.wait()
        except Exception as ex:
            if on_output:
                on_output(f"[BŁĄD] {ex}")
        finally:
            if on_stop:
                on_stop()

    threading.Thread(target=_run, daemon=True).start()
