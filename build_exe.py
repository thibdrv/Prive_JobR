"""Builds dist/RetrieveJob/RetrieveJob.exe, which works without installing Python, and dist/RetrieveJob-windows.zip
to share it.

The app is a folder (the .exe next to an _internal folder), not a single .exe: a single .exe unpacks its 16 MB into
a temporary folder at every start, which makes it slow to open. Keep the two together; the zip holds both.
Your results and settings, if you use the app from dist/RetrieveJob, are kept when it is built again.

Run it with the app's Python, once app.py has been opened at least once:
    .venv\\Scripts\\python.exe build_exe.py
Each system builds its own program, it can't be made for another one: on Linux this gives dist/RetrieveJob/RetrieveJob
and dist/RetrieveJob-linux.tar.gz (on GitHub, .github/workflows/release.yml builds both versions at each release).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "RetrieveJob"
APP = HERE / "dist" / NAME  # the folder to use or share
STAGING = HERE / "build" / "dist"  # PyInstaller writes here first, so it never empties the folder you use


def main() -> int:
    print("Installation de PyInstaller et des modules de l'application…")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check",
                    "-r", str(HERE / "requirements.txt"), "pyinstaller>=6.10"], check=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", NAME,
        "--add-data", f"{HERE / 'assets' / 'icon.png'}{os.pathsep}assets",
        "--add-data", f"{HERE / 'assets' / 'icon.ico'}{os.pathsep}assets",
        "--hidden-import", "retrieve_jobs",  # the search, run by "RetrieveJob.exe --search"
        "--distpath", str(STAGING), "--workpath", str(HERE / "build" / "work"), "--specpath", str(HERE / "build"),
    ]
    if os.name == "nt":
        command += ["--icon", str(HERE / "assets" / "icon.ico")]
    print("Construction de l'application (une à deux minutes)…")
    subprocess.run(command + [str(HERE / "app.py")], check=True, cwd=HERE)

    # Only the program goes in place: results/, settings.json, .cache/ already in the folder stay as they are
    built = STAGING / NAME
    APP.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(APP / "_internal", ignore_errors=True)
    for item in built.iterdir():
        target = APP / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    old_single_file = HERE / "dist" / f"{NAME}.exe"  # built by the earlier versions of this script
    old_single_file.unlink(missing_ok=True)

    # The archive to share: the program only, never your results or settings. On Linux a .tar.gz, which keeps the
    # program runnable once unpacked (a zip may lose that)
    system = "windows" if os.name == "nt" else "mac" if sys.platform == "darwin" else "linux"
    archive = shutil.make_archive(str(HERE / "dist" / f"{NAME}-{system}"), "gztar" if system == "linux" else "zip",
                                  root_dir=STAGING, base_dir=NAME)
    shutil.rmtree(HERE / "build", ignore_errors=True)
    program = APP / (f"{NAME}.exe" if os.name == "nt" else NAME)
    size = sum(path.stat().st_size for path in APP.rglob("*") if path.is_file()) / 1e6
    print(f"\nPrêt : {program} (dossier de {size:.0f} Mo), et {Path(archive).name} pour le partager.")
    print(f"Garde {program.name} avec son dossier _internal. Il range ses résultats et ses paramètres dans son "
          "dossier.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
