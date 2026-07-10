"""
Moddy – kompletny build.

Kroki:
  1. Buduje dist/Moddy/Moddy.exe  (one-folder, szybki start)
  2. Buduje dist/uninstall.exe    (mały, one-file)
  3. Kopiuje uninstall.exe → dist/Moddy/
  4. Buduje dist/Moddy_Beta_1.0_Setup.exe  (one-file, zawiera całą apkę)

Użycie:
  python build.py            – pełny build
  python build.py --app      – tylko apka (krok 1)
  python build.py --setup    – tylko instalator (kroki 2-4, apka musi istnieć)
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT         = Path(__file__).parent
DIST         = ROOT / "dist"
APP_DIR      = DIST / "Moddy"
APP_EXE      = APP_DIR / "Moddy.exe"
UNINST_EXE   = DIST / "uninstall.exe"
SETUP_EXE    = DIST / "Moddy_Beta_1.0_Setup.exe"
SPEC_APP     = ROOT / "Moddy.spec"
SPEC_UNINST  = ROOT / "installer_src" / "uninstall.spec"
SPEC_SETUP   = ROOT / "installer_src" / "setup.spec"


def _run(cmd):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"  ❌ Błąd (kod {r.returncode})")
        sys.exit(r.returncode)


def _mb(path: Path) -> str:
    return f"{path.stat().st_size / 1024 / 1024:.1f} MB"


def _write_version():
    try:
        from app.version import VERSION, BUILD_NAME
    except ImportError:
        VERSION, BUILD_NAME = "1.0.0-beta", "Beta 1.0"
    v = (VERSION.split("-")[0] + ".0.0").split(".")
    txt = (
        "VSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers=({v[0]},{v[1]},{v[2]},0),"
        f"prodvers=({v[0]},{v[1]},{v[2]},0),\n"
        "    mask=0x3f,flags=0x0,OS=0x40004,fileType=0x1,subtype=0x0,date=(0,0)),\n"
        "  kids=[StringFileInfo([StringTable(u'040904B0',[\n"
        f"    StringStruct(u'FileDescription',u'Moddy Launcher {BUILD_NAME}'),\n"
        f"    StringStruct(u'FileVersion',u'{VERSION}'),\n"
        "    StringStruct(u'ProductName',u'Moddy Launcher'),\n"
        f"    StringStruct(u'ProductVersion',u'{VERSION}'),\n"
        "    StringStruct(u'LegalCopyright',u'Copyright 2025 Moddy'),\n"
        "    StringStruct(u'OriginalFilename',u'Moddy.exe'),\n"
        "  ])]),VarFileInfo([VarStruct(u'Translation',[1045,1200])])]\n"
        ")\n"
    )
    (ROOT / "assets" / "version_info.txt").write_text(txt, encoding="utf-8")
    print(f"  Wersja: {VERSION} ({BUILD_NAME})")


def step_app():
    print("\n── [1/4] Budowanie apki (one-folder) ──────────────")
    _write_version()

    # Wyczyść
    for d in (ROOT / "build", APP_DIR):
        if d.exists():
            shutil.rmtree(d)

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC_APP)])

    if not APP_EXE.exists():
        print("  ❌ Moddy.exe nie powstał")
        sys.exit(1)
    print(f"  ✅ {APP_DIR}  ({_mb(APP_EXE)} exe + folder)")


def step_uninstaller():
    print("\n── [2/4] Budowanie uninstall.exe ───────────────────")

    if UNINST_EXE.exists():
        UNINST_EXE.unlink()

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
          str(SPEC_UNINST)])

    uninst_src = DIST / "uninstall.exe"
    if not uninst_src.exists():
        # PyInstaller może wrzucić do podkatalogu
        alt = DIST / "uninstall" / "uninstall.exe"
        if alt.exists():
            shutil.move(str(alt), str(uninst_src))
            shutil.rmtree(DIST / "uninstall", ignore_errors=True)

    if not uninst_src.exists():
        print("  ❌ uninstall.exe nie powstał")
        sys.exit(1)
    print(f"  ✅ {uninst_src}  ({_mb(uninst_src)})")


def step_copy_uninstaller():
    print("\n── [3/4] Kopiowanie uninstall.exe do apki ──────────")
    dest = APP_DIR / "uninstall.exe"
    shutil.copy2(UNINST_EXE, dest)
    print(f"  ✅ {dest}")


def step_setup():
    print("\n── [4/4] Budowanie instalatora (one-file) ──────────")

    if SETUP_EXE.exists():
        SETUP_EXE.unlink()

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
          str(SPEC_SETUP)])

    # PyInstaller może wrzucić do dist/Moddy_Beta_1.0_Setup/
    alt = DIST / "Moddy_Beta_1.0_Setup" / "Moddy_Beta_1.0_Setup.exe"
    if not SETUP_EXE.exists() and alt.exists():
        shutil.move(str(alt), str(SETUP_EXE))
        shutil.rmtree(alt.parent, ignore_errors=True)

    if not SETUP_EXE.exists():
        print("  ❌ Instalator nie powstał")
        sys.exit(1)
    print(f"  ✅ {SETUP_EXE}  ({_mb(SETUP_EXE)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app",   action="store_true", help="Tylko apka")
    ap.add_argument("--setup", action="store_true", help="Tylko instalator")
    args = ap.parse_args()

    print("╔══════════════════════════════╗")
    print("║   Moddy Launcher – Build     ║")
    print("╚══════════════════════════════╝")
    t0 = time.time()

    if args.app:
        step_app()
    elif args.setup:
        if not APP_EXE.exists():
            print("❌ Najpierw zbuduj apkę: python build.py --app")
            sys.exit(1)
        step_uninstaller()
        step_copy_uninstaller()
        step_setup()
    else:
        step_app()
        step_uninstaller()
        step_copy_uninstaller()
        step_setup()

    print(f"\n{'─'*40}")
    if SETUP_EXE.exists():
        print(f"  Instalator:  {SETUP_EXE}")
        print(f"  Rozmiar:     {_mb(SETUP_EXE)}")
    print(f"  Czas:        {time.time()-t0:.0f}s")
    print(f"{'─'*40}\n")


if __name__ == "__main__":
    main()
