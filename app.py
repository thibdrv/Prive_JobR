"""Retrieve Job: the app window. Choose what you are looking for, start the search, go through the offers.

Double-click this file, or run: python app.py
The first start installs what the search needs (about a minute).
Built as an .exe (build_exe.py), the same file also runs the search: RetrieveJob.exe --search
"""
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import settings as app_settings
from i18n import LANGUAGES, _, set_language
from window.common import (APP_DIR, CODE_DIR, DENSITIES, FROZEN, HEADER_COLORS, KEY, MENU_KEY, ROW_HEIGHT,
                           SEARCH_BUTTON, STATUS_ROWS, STATUSES, TEXT_SIZES, TITLE, Scrollable, scale_fonts,
                           use_installed_packages)
from window.companies_tab import CompaniesTab
from window.file_worker import FileWorker
from window.info_tab import InfoTab
from window import theme
from window.results_tab import ResultsTab
from window.search_tab import SearchTab
from window.settings_tabs import SettingsTabs
from window.watchdog import Watchdog

STARTED = time.monotonic()  # when the app started, for the start time noted in .cache/slow.log


class App(ResultsTab, SettingsTabs, CompaniesTab, SearchTab, InfoTab):
    """The app window: its parts come from the window package, one file per tab."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.messages: queue.Queue = queue.Queue()
        self.files = FileWorker(self.messages)  # reads and writes jobs.xlsx without freezing the window
        self.rebuilding = False  # the look is changing: see _with_fewer_widgets
        self.offers_version = 0  # goes up at each change of the offers: Statistics then draws them again
        self.stats_drawn = None  # (offers_version, theme, background) Statistics shows
        self.loads = self.loaded = 0  # readings of jobs.xlsx asked, and the latest one shown
        self.after_load = None  # what to do once the reading asked is shown
        self.error_shown = False
        self.process: subprocess.Popen | None = None
        self.ready = False
        self.offers: list[dict] = []
        self.descriptions: dict[str, str] = {}
        self.sort = ("", False)
        self.run: dict = {}  # progress of the running search
        settings = app_settings.load()
        set_language(settings["language"])
        self.theme = settings["theme"]
        self.text_size, self.density = settings["text_size"], settings["density"]
        use_installed_packages()  # openpyxl, for reading jobs.xlsx (missing only before the first install)
        root.title(TITLE)
        root.geometry("1100x760")
        root.minsize(900, 560)
        scale_fonts(TEXT_SIZES.get(self.text_size, TEXT_SIZES["normal"])[1])  # before the widgets that use them
        # One or the other: on Windows, setting both makes the taskbar fall back to Python's icon
        if os.name == "nt" and (CODE_DIR / "assets" / "icon.ico").exists():
            root.iconbitmap(default=str(CODE_DIR / "assets" / "icon.ico"))
        elif (CODE_DIR / "assets" / "icon.png").exists():
            self.icon = tk.PhotoImage(file=str(CODE_DIR / "assets" / "icon.png"))
            root.iconphoto(True, self.icon)

        header = tk.Frame(root, padx=14, pady=10)  # coloured band, recoloured with the theme
        header.pack(fill="x")
        self.header_icon = (tk.PhotoImage(file=str(CODE_DIR / "assets" / "icon.png")).subsample(2)
                            if (CODE_DIR / "assets" / "icon.png").exists() else None)
        self.header_parts = [header,
                             tk.Label(header, image=self.header_icon) if self.header_icon else tk.Label(header),
                             tk.Label(header, text=TITLE, font="RJTitle"),
                             tk.Label(header, text=_("les offres qui te correspondent, sur tous les sites"))]
        for part in self.header_parts[1:]:
            part.pack(side="left", padx=(0, 10))
        self.text_var = tk.StringVar(value=self.text_size)
        self.density_var = tk.StringVar(value=self.density)
        self.language_var = tk.StringVar(value=settings["language"])
        self.theme_var = tk.StringVar(value=self.theme)
        settings_button = ttk.Menubutton(header, text="⚙  " + _("Réglages"))
        settings_button.configure(menu=self._settings_menu(settings_button))
        settings_button.pack(side="right")

        bar = ttk.Frame(root, padding=(10, 8, 10, 10))
        bar.pack(side="bottom", fill="x")  # packed before the tabs, so a small window cuts the tabs, not the bar
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(8, 0))
        self.results_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.results_tab, text=_("Résultats"))
        self.stats_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.stats_tab, text=_("Statistiques"))
        # The settings tabs are built the first time they are opened: drawing all of them took seconds
        self.built = False
        self.stats = None
        self.lazy_tabs: dict[str, tuple] = {}  # tabs not built yet: path -> (frame, function that builds it)
        self.tab_builders: dict[str, tuple] = {}  # every such tab
        self.types_tab = self._tab(_("Postes"), self._build_types)
        self._tab(_("Expérience et villes"), self._build_filters)
        self._tab(_("Autres filtres"), self._build_more_filters)
        self._tab(_("Sites"), self._build_sites)
        self.companies_tab = self._tab(_("Entreprises"), self._build_companies)
        self.search_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.search_tab, text=_("Recherche"))
        self._tab(_("Informations"), self._build_info, scroll=False)  # a text block that scrolls by itself
        self._make_settings_variables()
        self.company_rows: list[dict] = []
        self.company_data: list[dict] = []
        self.companies_keep_all = tk.BooleanVar()
        self.check_online = tk.BooleanVar()
        self._build_results(self.results_tab)
        self._build_search(self.search_tab)
        self._fill_form(settings)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())

        self.search_button = tk.Button(bar, command=self.toggle_search, font="RJBold", relief="flat", borderwidth=0,
                                       foreground="#ffffff", activeforeground="#ffffff", disabledforeground="#f2f2f2",
                                       padx=14, pady=5, width=22, cursor="hand2")
        self.search_button.bind("<Enter>", lambda e: self._search_button_color(hover=True))
        self.search_button.bind("<Leave>", lambda e: self._search_button_color(hover=False))
        self._search_button_look("preparing")
        self.search_button.pack(side="left")
        progress_box = ttk.Frame(bar)
        progress_box.pack(side="left", fill="x", expand=True, padx=12)
        self.progress = ttk.Progressbar(progress_box, maximum=100)
        self.progress.pack(fill="x")
        self.status = ttk.Label(progress_box, text="", style="Hint.TLabel")
        self.status.pack(anchor="w")
        self.save_button = ttk.Button(bar, text=_("Enregistrer les paramètres"), command=self.save_settings)
        root.bind(f"<{KEY}-s>", lambda e: self.save_settings())
        root.bind(f"<{KEY}-S>", lambda e: self.save_settings())
        root.bind("<F5>", lambda e: self.load_offers())
        self.built = True

        self._apply_theme()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.watchdog = Watchdog(root, self._where)  # notes in .cache what holds the window, if anything does
        self.start_noted = False
        root.after(50, self._poll)
        root.after(1000, self._tick)
        threading.Thread(target=self._prepare, daemon=True).start()

    # ---- look and language ----

    def _settings_menu(self, parent) -> tk.Menu:
        """The "Réglages" menu: display, language and theme, then saving or resetting the settings."""
        menu = tk.Menu(parent, tearoff=False)
        submenus = [
            (_("Taille du texte"), self.text_var, [(code, _(name)) for code, (name, _f) in TEXT_SIZES.items()],
             self.change_display),
            (_("Lignes du tableau"), self.density_var, [(code, _(name)) for code, (name, _f) in DENSITIES.items()],
             self.change_display),
            (_("Thème"), self.theme_var, [("light", _("Clair")), ("dark", _("Sombre"))], self.change_theme),
            (_("Langue"), self.language_var, list(LANGUAGES.items()), self.change_language),
        ]
        for label, variable, choices, command in submenus:
            submenu = tk.Menu(menu, tearoff=False)
            for code, name in choices:
                submenu.add_radiobutton(label=name, value=code, variable=variable, command=command)
            menu.add_cascade(label=label, menu=submenu)
        menu.add_separator()
        menu.add_command(label=_("Enregistrer les paramètres"), accelerator=f"{MENU_KEY}S", command=self.save_settings)
        menu.add_command(label=_("Paramètres par défaut…"), command=self.reset_settings)
        menu.add_separator()
        menu.add_command(label=_("Actualiser les résultats"), accelerator="F5", command=self.load_offers)
        return menu

    def _tab_changed(self) -> None:
        """Builds a tab the first time it is opened; the save button shows only on the tabs that hold settings."""
        lazy = self.lazy_tabs.pop(self.notebook.select(), None)
        if lazy:
            inner, build = lazy
            build(inner)
        if 2 <= self.notebook.index("current") <= self.notebook.index(self.search_tab):  # not Information
            self.save_button.pack(side="right")
        else:
            self.save_button.pack_forget()
        self._show_stats()

    def _tab(self, title: str, build, scroll: bool = True) -> ttk.Frame:
        """A tab whose widgets build(inner) makes the first time it is opened; scrolling unless scroll is False."""
        frame = Scrollable(self.notebook) if scroll else ttk.Frame(self.notebook, padding=(14, 12))
        inner = frame.inner if scroll else frame
        self.notebook.add(frame, text=title)
        self.lazy_tabs[str(frame)] = self.tab_builders[str(frame)] = (inner, build)
        return inner

    def _apply_theme(self) -> None:
        dark = self.theme == "dark"
        palette = theme.apply(self.root, self.theme)
        style = ttk.Style()
        self.background, text = palette["bg"], palette["text"]
        style.configure("Hint.TLabel", foreground=palette["muted"])
        self._apply_display()
        for canvas in self.root.winfo_children():
            self._recolor(canvas, self.background)
        self.text_colors = ("#2b2b2b" if dark else "#ffffff", text)
        for box in (self.log, self.description):
            box.configure(background="#202020" if dark else "#ffffff", foreground=text, insertbackground=text)
        self.description.tag_configure("match", background="#6b5900" if dark else "#fff176")  # searched words
        self._style_texts()
        for status, (light, dark_color) in STATUS_ROWS.items():
            self.table.tag_configure(f"status{STATUSES.index(status)}", background=dark_color if dark else light)
        self.table.tag_configure("new", background="#5a4a00" if dark else "#fff4a8")
        band, title, subtitle = HEADER_COLORS[self.theme]
        for part in self.header_parts:
            part.configure(background=band)
        self.header_parts[2].configure(foreground=title)
        self.header_parts[3].configure(foreground=subtitle)
        self.table.tag_configure("expired", foreground="#7a7a7a" if dark else "#a0a0a0")
        self._show_stats()

    def _style_texts(self) -> None:
        """The multi-line boxes are plain tk widgets: they need the theme's colours by hand."""
        background, text = getattr(self, "text_colors", ("#ffffff", "#1c1c1c"))
        for row in self.type_rows:
            for key in ("searches", "words"):
                row[key].configure(background=background, foreground=text, insertbackground=text)

    def _recolor(self, widget, background: str) -> None:
        if isinstance(widget, tk.Canvas):
            widget.configure(background=background)
        for child in widget.winfo_children():
            self._recolor(child, background)

    def _apply_display(self) -> None:
        """Text size and row height: the fonts (the theme's too) and the table rows follow them."""
        text = TEXT_SIZES.get(self.text_size, TEXT_SIZES["normal"])[1]
        rows = DENSITIES.get(self.density, DENSITIES["normal"])[1]
        changed = scale_fonts(text)
        style = ttk.Style()
        height = round(ROW_HEIGHT * text * rows)
        if str(style.lookup("Treeview", "rowheight")) != str(height):  # same reason: only when it changes
            style.configure("Treeview", rowheight=height)
            changed = True
        if changed and self.built:
            self._show_stats()
            self._fit_width()

    def _with_fewer_widgets(self, change) -> None:
        """Runs a change that makes Tk lay every widget out again (text size, theme) with as few widgets as possible.

        Tk lays the whole window out again for each font changed, and each widget of the Windows 11 theme is slow
        to lay out: with every tab built and 300 table rows that took 5 seconds, and Windows said the app was not
        responding. So the table is emptied and the tabs already opened are taken down meanwhile; they are built
        again, with the new look, when they are next shown (their values stay in their variables).
        """
        selection = self.table.selection()
        self.table.delete(*self.table.get_children())
        self._forget_built_tabs()
        self.rebuilding = True  # Statistics is drawn once, at the end, not at each step of the change
        try:
            change()
        finally:
            self.rebuilding = False
            self._tab_changed()  # builds again the tab on screen, if it was one of them
            self._show_offers()
            self.table.selection_set([iid for iid in selection if self.table.exists(iid)])

    def _forget_built_tabs(self) -> None:
        self.type_data, self.company_data = self._types_from_form(), self._companies_from_form()
        self.types_built = self.companies_built = False
        self.type_rows, self.company_rows = [], []
        for key, (inner, build) in self.tab_builders.items():
            if key not in self.lazy_tabs:
                for child in inner.winfo_children():
                    child.destroy()
                self.lazy_tabs[key] = (inner, build)
        if self.stats is not None:
            for child in self.stats_tab.winfo_children():
                child.destroy()
            self.stats = None

    def _fit_width(self) -> None:
        """Widens the window when bigger text no longer fits in it, as far as the screen allows."""
        self.root.update_idletasks()
        rows = [self.root.winfo_children()[0],  # the header, the filter rows and the buttons, not the table
                *(row for row in self.results_tab.winfo_children() if not isinstance(row, ttk.PanedWindow))]
        needed = max(row.winfo_reqwidth() for row in rows) + 50  # margins of the tabs
        width = min(needed, self.root.winfo_screenwidth() - 40)
        if self.root.winfo_width() < width:
            self.root.geometry(f"{width}x{self.root.winfo_height()}")

    def change_display(self) -> None:
        """Applies the text size and row height chosen in the menu, and keeps them for next time."""
        self.text_size, self.density = self.text_var.get(), self.density_var.get()
        self._with_fewer_widgets(self._apply_display)
        settings = app_settings.load()
        settings["text_size"], settings["density"] = self.text_size, self.density
        app_settings.save(settings)

    def change_theme(self) -> None:
        self.theme = self.theme_var.get()
        self._with_fewer_widgets(self._apply_theme)
        settings = app_settings.load()
        settings["theme"] = self.theme
        app_settings.save(settings)

    def change_language(self) -> None:
        """Saves the language and opens the window again in it (your unsaved settings are kept)."""
        code = self.language_var.get()
        if self.process:
            messagebox.showinfo(TITLE, _("Attends la fin de la recherche pour changer de langue."))
            self.language_var.set(app_settings.load()["language"])
            return
        settings = self._settings_from_form() or app_settings.load()
        settings["language"] = code
        app_settings.save(settings)
        if FROZEN:
            command = [sys.executable, *sys.argv[1:]]
        else:
            command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
        self.files.wait(20)
        release_window_lock()
        subprocess.Popen(command, cwd=APP_DIR, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        self.root.destroy()

    # ---- plumbing ----

    def _poll(self) -> None:
        """Handles what the threads and the search sent, a limited number at a time so the window keeps answering."""
        try:
            for _message in range(200):
                if self.messages.empty():
                    break
                self._handle(*self.messages.get())
        finally:  # an error in one message must not stop all the next ones
            self.root.after(50, self._poll)  # what the threads send shows within 50 ms

    def _handle(self, kind: str, message) -> None:
        if kind == "log":
            self._write(message)
        elif kind == "event":
            self._on_event(message)
        elif kind == "ready":
            self.ready = True
            self._search_button_look("start")
            self.load_offers()
            self._show_backups()
            self._write(_("Prêt. Règle les paramètres puis clique sur « Lancer la recherche » "
                          "(5 à 15 minutes la première fois).") + "\n")
        elif kind == "daily":
            self._show_daily(message)
        elif kind == "call":
            message()
        elif kind == "done":
            self._finish(message)

    def _search_button_look(self, look: str) -> None:
        """Green "Start the search", red "Stop the search", grey while preparing."""
        self.search_look = look
        self.search_button.configure(text=_(SEARCH_BUTTON[look][0]),
                                     state="disabled" if look == "preparing" else "normal")
        self._search_button_color(hover=False)

    def _search_button_color(self, hover: bool) -> None:
        _text, color, darker = SEARCH_BUTTON[self.search_look]
        shown = darker if hover and self.search_look != "preparing" else color
        self.search_button.configure(background=shown, activebackground=darker)

    def _where(self) -> str:
        """The tab on screen (and the sub-tab of Statistics), for the slow moments noted in .cache/slow.log."""
        where = self.notebook.tab("current", "text")
        if self.stats is not None and self.notebook.select() == str(self.stats_tab):
            where += " / " + self.stats.pages.tab("current", "text")
        return where

    def _tick(self) -> None:
        self._show_progress()
        self.root.after(1000, self._tick)

    def _write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self) -> None:
        if self.process:
            if not messagebox.askyesno(TITLE, _("Une recherche est en cours. L'arrêter et quitter ?")):
                return
            self.process.terminate()
        elif self._unsaved_settings():
            answer = messagebox.askyesnocancel(TITLE, _("Tu as modifié des paramètres sans les enregistrer. "
                                                        "Les enregistrer avant de quitter ?"))
            if answer is None or (answer and not self.save_settings()):
                return  # Cancel, or settings that can't be saved (a number field left empty)
        self.status.configure(text=_("Enregistrement…"))
        self.root.update_idletasks()
        self.files.wait(20)  # the last status or note changes reach jobs.xlsx before the app stops
        self.root.destroy()

    def _unsaved_settings(self) -> bool:
        """True when the form differs from settings.json (the theme, language and display are saved at once)."""
        saved = app_settings.load()
        try:
            form = self._settings_from_form(quiet=True)
        except (tk.TclError, ValueError):
            return True
        return form is None or form != saved


def restart_without_console() -> bool:
    """On a double-click, Windows opens a terminal next to the app: start again with pythonw, which opens none.

    Returns True when the app was restarted, so this copy can stop.
    """
    if os.name != "nt" or FROZEN or sys.stdout is None:  # sys.stdout is None: already without a console
        return False
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        return False
    subprocess.Popen([str(pythonw), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=APP_DIR,
                     creationflags=subprocess.DETACHED_PROCESS)
    return True


def use_own_taskbar_button() -> None:
    """Makes Windows show the app's own icon in the taskbar, not Python's (call before opening the window)."""
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RetrieveJob.App")


_instance_lock = None  # the open lock file that says the window is open; closed when the app stops


def first_window() -> bool:
    """True for the first window of the app. A second one would save jobs.xlsx at the same time as the first and
    lose changes: instead, the window already open comes to the front."""
    global _instance_lock
    path = APP_DIR / ".cache" / "window.lock"
    try:
        path.parent.mkdir(exist_ok=True)
        _instance_lock = path.open("a+")
        if os.name == "nt":
            import msvcrt
            _instance_lock.seek(0)
            msvcrt.locking(_instance_lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:  # held by the window already open (an unwritable folder would fail later, more clearly)
        if _instance_lock is None:
            return True
        _instance_lock.close()
        _instance_lock = None
        if os.name == "nt":
            import ctypes
            window = ctypes.windll.user32.FindWindowW(None, TITLE)
            if window:
                ctypes.windll.user32.ShowWindow(window, 9)  # restored if it was minimised
                ctypes.windll.user32.SetForegroundWindow(window)
        return False


def release_window_lock() -> None:
    """Lets a new window open (the one that replaces this one in another language)."""
    global _instance_lock
    if _instance_lock is not None:
        _instance_lock.close()
        _instance_lock = None


def hide_own_console() -> None:
    """Hides the black window Windows opens on double-click, but never a terminal you started it from."""
    if os.name != "nt":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    if kernel32.GetConsoleProcessList((ctypes.c_uint * 2)(), 2) == 1:  # we are alone in this console
        ctypes.windll.user32.ShowWindow(kernel32.GetConsoleWindow(), 0)


def main() -> None:
    """Opens the window (or, with --search, runs the search: the .exe and the automatic search use it)."""
    hide_own_console()
    if "--search" in sys.argv:  # the .exe running a search for the window or the daily task
        import retrieve_jobs
        sys.exit(retrieve_jobs.main([arg for arg in sys.argv[1:] if arg != "--search"]))
    if restart_without_console():
        sys.exit(0)
    if not first_window():
        sys.exit(0)
    use_own_taskbar_button()
    window = tk.Tk()
    App(window)
    window.mainloop()


if __name__ == "__main__":
    main()
