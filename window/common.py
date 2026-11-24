"""What every part of the window shares: paths, table columns, statuses, small helpers."""
import importlib.util
import os
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import ttk

import settings as app_settings

FROZEN = getattr(sys, "frozen", False)  # running as the .exe
MAC = sys.platform == "darwin"
# Shortcuts: Cmd on a Mac, Ctrl elsewhere. KEY is the name in Tk bindings ("<Command-s>"), MENU_KEY how a menu
# shows it (Tk draws "Command-S" as ⌘S on a Mac), KEY_NAME how the help text names it.
KEY, MENU_KEY, KEY_NAME = ("Command", "Command-", "Cmd+") if MAC else ("Control", "Ctrl+", "Ctrl+")


def with_key_name(text: str) -> str:
    """A help text with the shortcut key of this computer: "Ctrl+S" becomes "Cmd+S" on a Mac."""
    return text.replace("Ctrl+", KEY_NAME)
CODE_DIR = Path(__file__).resolve().parent.parent  # the project folder
APP_DIR = app_settings.APP_DIR
VENV = APP_DIR / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PYTHONW = VENV / "Scripts/pythonw.exe" if os.name == "nt" else PYTHON  # no black window for the daily search
REQUIREMENTS = CODE_DIR / "requirements.txt"
INSTALLED = VENV / "installed_requirements.txt"  # copy of requirements.txt at the last install
EXCEL_FILE = APP_DIR / "results" / "jobs.xlsx"
HISTORY_FILE = APP_DIR / ".cache" / "history.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TITLE = "Retrieve Job"
# Results table: column -> (heading, width); the headings are translated when shown
TABLE_COLUMNS = {"Score": ("Score", 45), "Titre": ("Titre", 250), "Statut": ("Statut", 85),
                 "Entreprise": ("Entreprise", 115), "Ville": ("Ville", 90), "Catégorie": ("Catégorie", 115),
                 "Expérience": ("Expérience", 75), "Contrat": ("Contrat", 85), "Mode de travail": ("Mode", 75),
                 "Salaire": ("Salaire", 90), "Site": ("Site", 85)}
TRANSLATED_COLUMNS = {"Statut", "Catégorie", "Expérience", "Contrat", "Mode de travail", "Salaire"}
STATUSES = ["À voir", "Postulé", "Entretien", "Refusé", "Pas intéressé"]
ALL = "Toutes"
NO_STATUS = "Sans statut"
NOT_STATED = "(non précisé)"  # filter choice for offers that don't say their site, work mode or contract
EXPIRED = "expirée"  # results_file.EXPIRED, without importing openpyxl before it is installed
WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
# Badge next to each offer in the table; the status is also written in its column, so colour is never alone
STATUS_COLORS = {"À voir": "#e0a106", "Postulé": "#2a78d6", "Entretien": "#2e9e5b", "Refusé": "#d1495b",
                 "Pas intéressé": "#8a8a8a"}
# Pale background of a table row by its status (light theme, dark theme): where each offer stands at a glance
# ("À voir" keeps the plain background: its amber would look like the yellow of the new offers)
STATUS_ROWS = {"Postulé": ("#e3edfb", "#1d3350"),
               "Entretien": ("#e1f3e7", "#1d3b29"), "Refusé": ("#fae3e5", "#47242a"),
               "Pas intéressé": ("#ececec", "#2f2f2f")}
# The search button: text, colour, colour under the mouse (white text: 5:1 contrast or more on both)
SEARCH_BUTTON = {"preparing": ("Préparation…", "#8a8a8a", "#8a8a8a"),
                 "start": ("Lancer la recherche", "#2e7d32", "#246428"),
                 "stop": ("Arrêter la recherche", "#c62828", "#a51f1f")}
# Header band: background, title, subtitle
HEADER_COLORS = {"light": ("#1f5fbf", "#ffffff", "#d6e4fa"), "dark": ("#1a3f73", "#ffffff", "#b9cdea")}
# Category dots: the same hues, in the same order, as the pale category cells of jobs.xlsx
CATEGORY_DOTS = ["#2a78d6", "#3a9a46", "#e07b39", "#8e5cc7", "#2a9d9d", "#c9a116", "#d1495b", "#8a8a8a"]
# Text size and row height, chosen at the top of the window: setting value -> (name shown, factor)
TEXT_SIZES = {"small": ("Petit", 0.9), "normal": ("Normal", 1.0), "large": ("Grand", 1.15),
              "xlarge": ("Très grand", 1.3)}
DENSITIES = {"compact": ("Compactes", 0.8), "normal": ("Normales", 1.0), "airy": ("Aérées", 1.3)}
ROW_HEIGHT = 26  # pixels of a table row at normal size
# Fonts of the window, by name, so that changing the text size changes them everywhere at once
FONTS = {"RJText": ("Segoe UI", 9, "normal"), "RJBold": ("Segoe UI", 9, "bold"), "RJSection": ("Segoe UI", 10, "bold"),
         "RJTitle": ("Segoe UI", 16, "bold"), "RJNumber": ("Segoe UI", 20, "bold"), "RJLog": ("Consolas", 9, "normal")}
_base_sizes: dict[str, int] = {}
_fonts: dict[str, tkfont.Font] = {}


def split_list(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,\n]", text) if item.strip()]


def join_list(items: list[str]) -> str:
    return ", ".join(items)


def duration(seconds: float) -> str:
    minutes, seconds = divmod(max(0, round(seconds)), 60)
    return f"{minutes} min {seconds:02d} s" if minutes else f"{seconds} s"


def use_installed_packages() -> bool:
    """Lets this window use what the search installed (openpyxl, requests...); True when they are there."""
    if not FROZEN:  # where venv puts them: no need to search the thousands of files of .venv (0.15 s)
        for folder in (VENV / "Lib" / "site-packages",
                       VENV / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"):
            if folder.is_dir() and str(folder) not in sys.path:
                sys.path.append(str(folder))
    return importlib.util.find_spec("openpyxl") is not None


def company_from_link(link: str) -> dict | None:
    """{"platform", "id"} from a careers-page link such as https://jobs.lever.co/capital."""
    patterns = {"greenhouse": r"greenhouse\.io/(?:embed/job_board\?for=)?([\w.-]+)",
                "lever": r"lever\.co/([\w.-]+)", "workable": r"workable\.com/([\w.-]+)",
                "smartrecruiters": r"smartrecruiters\.com/([\w.-]+)"}
    for platform, pattern in patterns.items():
        match = re.search(pattern, link)
        if match and match.group(1).lower() not in ("v0", "v1", "api", "j", "jobs", "view"):
            return {"platform": platform, "id": match.group(1)}
    return None


def scale_fonts(factor: float) -> bool:
    """Creates the window's fonts the first time, then sets every font (the theme's too) to factor × its size.

    Only the fonts whose size changes are touched: each change makes Tk lay the whole window out again,
    which takes seconds with a full table. Returns True when a font changed.
    """
    for name, (family, size, weight) in FONTS.items():
        if name not in tkfont.names():  # kept in _fonts: tkinter deletes a font once Python forgets it
            _fonts[name] = tkfont.Font(name=name, family=family, size=size, weight=weight)
    changed = False
    for name in tkfont.names():
        font = tkfont.nametofont(name)
        base = _base_sizes.setdefault(name, font.cget("size"))
        size = round(base * factor) or (1 if base > 0 else -1)  # negative sizes are in pixels
        if font.cget("size") != size:
            font.configure(size=size)
            changed = True
    return changed


def marker(category_color: str | None, status_color: str | None) -> tk.PhotoImage:
    """The little picture before each offer: a round dot for its category, a rounded badge for its status."""
    image = tk.PhotoImage(width=30, height=14)
    for y in range(14):
        for x in range(30):
            if category_color and (x - 6) ** 2 + (y - 7) ** 2 <= 25:  # dot, 11 pixels wide
                image.put(category_color, (x, y))
            elif status_color and 16 <= x <= 28 and 3 <= y <= 11 and not (x in (16, 28) and y in (3, 11)):
                image.put(status_color, (x, y))  # badge with its corners cut
    return image


class Scrollable(ttk.Frame):
    """A frame whose content scrolls when the window is too small for it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(14, 12))
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for widget in (self.canvas, self.inner):
            widget.bind("<Enter>", lambda e: self._listen_to_wheel(True))
            widget.bind("<Leave>", lambda e: self._listen_to_wheel(False))

    # The wheel: <MouseWheel> on Windows and Mac; on Linux, button 4 (up) and button 5 (down)
    WHEEL_EVENTS = ("<MouseWheel>", "<Button-4>", "<Button-5>")

    def _listen_to_wheel(self, on: bool) -> None:
        for event in self.WHEEL_EVENTS:
            if on:
                self.bind_all(event, self._wheel)
            else:
                self.unbind_all(event)

    def _wheel(self, event) -> None:
        if self.inner.winfo_height() > self.canvas.winfo_height():
            up = event.num == 4 or getattr(event, "delta", 0) > 0
            self.canvas.yview_scroll(-1 if up else 1, "units")
