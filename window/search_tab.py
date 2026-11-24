"""The Search tab: running the search with its progress, the automatic search, backups."""
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import venv
from pathlib import Path
from tkinter import messagebox, ttk

import desktop
from i18n import _
from window.common import (APP_DIR, CODE_DIR, FROZEN, HISTORY_FILE, INSTALLED, NO_WINDOW, PYTHON, PYTHONW,
                           REQUIREMENTS, TITLE, VENV, WEEKDAYS, duration, use_installed_packages)


class SearchTab:
    """The Search tab and the search itself. Part of App (app.py), so it shares its attributes."""

    def _build_search(self, tab: ttk.Frame) -> None:
        options = ttk.Frame(tab)
        options.pack(fill="x")
        self.open_when_done = tk.BooleanVar(value=False)
        self.notify = tk.BooleanVar()
        ttk.Checkbutton(options, text=_("Notification à la fin de la recherche"), variable=self.notify).pack(
            side="left")
        ttk.Checkbutton(options, text=_("Ouvrir Excel à la fin"), variable=self.open_when_done).pack(
            side="left", padx=16)
        self.last_run = ttk.Label(options, text="", style="Hint.TLabel")
        self.last_run.pack(side="right")
        checks = ttk.Frame(tab)
        checks.pack(fill="x", pady=(4, 0))
        self.check_online_box = ttk.Checkbutton(checks, text=_(
            "Vérifier à chaque recherche que les offres du fichier sont encore en ligne (les autres sont "
            "marquées « expirée »)"))
        self.check_online_box.pack(side="left")

        daily = ttk.LabelFrame(tab, text=_("Recherche automatique"), padding=8)
        daily.pack(fill="x", pady=(8, 8))
        self.daily_mode = tk.StringVar(value="days")
        self.daily_every = tk.IntVar(value=1)
        self.daily_hour = tk.IntVar(value=9)
        self.daily_minute = tk.IntVar(value=0)
        self.daily_weekdays = [tk.BooleanVar(value=day < 5) for day in range(7)]
        every = ttk.Frame(daily)
        every.pack(fill="x")
        ttk.Radiobutton(every, text=_("Tous les"), variable=self.daily_mode, value="days").pack(side="left")
        ttk.Spinbox(every, from_=1, to=30, width=4, textvariable=self.daily_every).pack(side="left", padx=4)
        ttk.Label(every, text=_("jour(s)")).pack(side="left")
        week = ttk.Frame(daily)
        week.pack(fill="x", pady=(4, 0))
        ttk.Radiobutton(week, text=_("Chaque semaine, le :"), variable=self.daily_mode, value="week").pack(side="left")
        for day, name in enumerate(WEEKDAYS):
            ttk.Checkbutton(week, text=_(name), variable=self.daily_weekdays[day]).pack(side="left", padx=(6, 0))
        when = ttk.Frame(daily)
        when.pack(fill="x", pady=(6, 0))
        ttk.Label(when, text=_("À")).pack(side="left")
        ttk.Spinbox(when, from_=0, to=23, width=4, format="%02.0f", textvariable=self.daily_hour).pack(
            side="left", padx=4)
        ttk.Label(when, text=":").pack(side="left")
        ttk.Spinbox(when, from_=0, to=55, increment=5, width=4, format="%02.0f", textvariable=self.daily_minute).pack(
            side="left", padx=4)
        ttk.Button(when, text=_("Programmer"), command=self.schedule).pack(side="left", padx=(12, 4))
        ttk.Button(when, text=_("Arrêter"), command=self.unschedule).pack(side="left")
        self.daily_status = ttk.Label(daily, text="", style="Hint.TLabel", wraplength=1000)
        self.daily_status.pack(anchor="w", pady=(6, 0))

        saves = ttk.LabelFrame(tab, text=_("Sauvegardes de jobs.xlsx"), padding=8)
        saves.pack(fill="x", pady=(0, 8))
        self.backups_to_keep = tk.IntVar(value=10)
        ttk.Label(saves, text=_("Avant chaque recherche, garder les")).pack(side="left")
        ttk.Spinbox(saves, from_=0, to=100, width=4, textvariable=self.backups_to_keep).pack(side="left", padx=4)
        ttk.Label(saves, text=_("dernières copies")).pack(side="left")
        ttk.Button(saves, text=_("Sauvegarder maintenant"), command=self.backup_now).pack(side="left", padx=(12, 4))
        ttk.Button(saves, text=_("Restaurer…"), command=self.restore_backup).pack(side="left")
        ttk.Button(saves, text=_("Ouvrir le dossier"), command=self.open_backups).pack(side="left", padx=4)
        self.backups_status = ttk.Label(saves, text="", style="Hint.TLabel")
        self.backups_status.pack(side="left", padx=8)

        log_frame = ttk.Frame(tab)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=12, wrap="word", state="disabled", relief="flat", borderwidth=8,
                           font="RJLog")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self._show_last_run()
        threading.Thread(target=lambda: self.messages.put(("daily", desktop.scheduled())), daemon=True).start()

    def _show_last_run(self) -> None:
        try:
            runs = json.loads(HISTORY_FILE.read_text(encoding="utf-8")).get("runs", [])
        except (OSError, ValueError):
            runs = []
        if runs:
            last = runs[-1]
            day, _sep, hour = last["date"].partition("T")
            self.last_run.configure(text=_("Dernière recherche : {day} à {hour}, {time}, {count} nouvelle(s) offre(s)")
                                    .format(day=day, hour=hour, time=duration(last["seconds"]), count=last["kept"]))

    # ---- backups ----

    def _show_backups(self) -> None:
        if not self.ready:
            return
        import results_file
        copies = results_file.backups()
        if copies:
            newest = copies[0].stem.removeprefix("jobs_").replace("_", " ").split(" ")
            self.backups_status.configure(text=_("{count} copie(s), la dernière le {day} à {hour}").format(
                count=len(copies), day=newest[0], hour=newest[-1].replace("-", ":")[:5]))
        else:
            self.backups_status.configure(text=_("Pas encore de copie."))

    def backup_now(self) -> None:
        if not self.ready:
            return
        import results_file
        if not results_file.EXCEL_FILE.exists():
            messagebox.showinfo(TITLE, _("Pas encore de résultats : lance d'abord une recherche."))
            return
        results_file.backup(max(1, int(self.backups_to_keep.get() or 1)))
        self._show_backups()

    def restore_backup(self) -> None:
        if not self.ready or self.process:
            messagebox.showinfo(TITLE, _("Attends la fin de la recherche pour modifier une offre."))
            return
        import results_file
        from tkinter import filedialog
        results_file.BACKUPS.mkdir(parents=True, exist_ok=True)
        chosen = filedialog.askopenfilename(title=_("Choisis la copie à remettre"), initialdir=results_file.BACKUPS,
                                            filetypes=[("Excel", "*.xlsx")])
        if not chosen:
            return
        if not messagebox.askyesno(TITLE, _("Remplacer jobs.xlsx par la copie « {name} » ? Le fichier actuel est "
                                            "d'abord sauvegardé, tu pourras revenir en arrière.").format(
                                                name=Path(chosen).name)):
            return
        keep = int(self.backups_to_keep.get() or 1)

        def done(_result) -> None:
            self.undo_steps.clear()  # they were about the file just replaced
            self.load_offers()
            self._show_backups()
            self.status.configure(text=_("Copie remise en place."))

        def failed(error: Exception) -> None:
            messagebox.showerror(TITLE, _("jobs.xlsx est ouvert dans Excel : ferme-le, puis recommence.") if isinstance(
                error, PermissionError) else _("La copie n'a pas pu être remise en place ({error}).").format(
                    error=error))
        self.files.add(lambda: results_file.restore(Path(chosen), keep), done, failed)

    def open_backups(self) -> None:
        import results_file
        results_file.BACKUPS.mkdir(parents=True, exist_ok=True)
        desktop.open_file(results_file.BACKUPS)

    # ---- automatic search ----

    def _daily_command(self) -> list[str]:
        if FROZEN:
            return [sys.executable, "--search"]
        return [str(PYTHONW), str(CODE_DIR / "retrieve_jobs.py")]

    def schedule(self) -> None:
        if not self.ready:
            messagebox.showinfo(TITLE, _("Attends la fin de l'installation."))
            return
        if not self.save_settings():
            return
        try:
            plan = {"hour": int(self.daily_hour.get()) % 24, "minute": int(self.daily_minute.get()) % 60,
                    "every_days": max(1, int(self.daily_every.get())), "weekdays": []}
        except (tk.TclError, ValueError):
            messagebox.showerror(TITLE, _("L'heure et le nombre de jours doivent être des nombres."))
            return
        if self.daily_mode.get() == "week":
            plan["every_days"] = 0
            plan["weekdays"] = [day for day, chosen in enumerate(self.daily_weekdays) if chosen.get()]
            if not plan["weekdays"]:
                messagebox.showerror(TITLE, _("Coche au moins un jour de la semaine."))
                return
        error = desktop.schedule(plan, self._daily_command())
        if error:
            messagebox.showerror(TITLE, _("La recherche automatique n'a pas pu être programmée :") + f"\n{error}")
        self._show_daily(desktop.scheduled())

    def unschedule(self) -> None:
        desktop.unschedule()
        self._show_daily(desktop.scheduled())

    def _show_daily(self, plan: dict | None) -> None:
        """Shows when the automatic search runs, and puts it back in the form."""
        if plan is None:
            self.daily_status.configure(text=_("Pas programmée."))
            return
        self.daily_hour.set(plan["hour"])
        self.daily_minute.set(plan["minute"])
        time_text = f"{plan['hour']:02d}:{plan['minute']:02d}"
        if plan["weekdays"]:
            self.daily_mode.set("week")
            for day, variable in enumerate(self.daily_weekdays):
                variable.set(day in plan["weekdays"])
            days = ", ".join(_(WEEKDAYS[day]) for day in plan["weekdays"])
            when = _("Programmée chaque {days} à {time}").format(days=days, time=time_text)
        else:
            self.daily_mode.set("days")
            self.daily_every.set(plan["every_days"])
            when = (_("Programmée tous les jours à {time}").format(time=time_text) if plan["every_days"] == 1 else
                    _("Programmée tous les {count} jours à {time}").format(count=plan["every_days"], time=time_text))
        self.daily_status.configure(text=when + _(" (avec les paramètres enregistrés). L'ordinateur doit être "
                                                  "allumé à cette heure-là."))

    # ---- search ----

    def _prepare(self) -> None:
        """Installs what the search needs, the first time and after requirements.txt changes."""
        if not FROZEN:
            try:
                if not PYTHON.exists():
                    self.messages.put(("log", _("Première utilisation : installation (environ une minute)…") + "\n"))
                    venv.create(VENV, with_pip=True)
                wanted = REQUIREMENTS.read_text(encoding="utf-8")
                if not INSTALLED.exists() or INSTALLED.read_text(encoding="utf-8") != wanted:
                    self.messages.put(("log", _("Installation des modules nécessaires…") + "\n"))
                    subprocess.run([PYTHON, "-m", "pip", "install", "-q", "--disable-pip-version-check",
                                    "-r", REQUIREMENTS], check=True, capture_output=True, creationflags=NO_WINDOW)
                    INSTALLED.write_text(wanted, encoding="utf-8")
            except (OSError, subprocess.CalledProcessError) as exc:
                self.messages.put(("log", _("L'installation a échoué ({error}). Vérifie ta connexion internet "
                                            "et relance l'application.").format(error=exc) + "\n"))
                return
            use_installed_packages()
        self.messages.put(("ready", None))

    def toggle_search(self) -> None:
        if self.process:
            self.process.terminate()
            self._write("\n" + _("Recherche arrêtée.") + "\n")
            return
        if not self.save_settings():
            return
        if not self.files.wait(15):  # the search rewrites jobs.xlsx: the changes being saved go first
            messagebox.showinfo(TITLE, _("Un changement est encore en cours d'enregistrement : réessaie dans un instant."))
            return
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        if FROZEN:
            command = [sys.executable, "--search", "--progress"]
        else:
            command = [str(PYTHON), "-u", str(CODE_DIR / "retrieve_jobs.py"), "--progress"]
        if self.open_when_done.get():
            command.append("--open")
        self.process = subprocess.Popen(
            command, cwd=APP_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=NO_WINDOW)
        self.run = {"started": time.monotonic(), "stage": 0, "done": 0, "total": 0, "pending": set(),
                    "stages": 3 if self.check_online.get() else 2, "stage_started": time.monotonic(),
                    "history": self._history()}
        self.progress.configure(value=0)
        self._search_button_look("stop")
        self.notebook.select(self.search_tab)
        threading.Thread(target=self._read_output, args=(self.process,), daemon=True).start()

    def _history(self) -> dict:
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _read_output(self, process: subprocess.Popen) -> None:
        for line in process.stdout:
            self.messages.put(("event", line[3:].split()) if line.startswith("@@ ") else ("log", line))
        self.messages.put(("done", process.wait()))

    def _on_event(self, parts: list[str]) -> None:
        run = self.run
        kind = parts[0]
        if kind == "stage":
            run.update(stage=int(parts[1]), total=int(parts[2]), done=0, stage_started=time.monotonic())
            if run["stage"] == 1:
                run["pending"] = set(parts[3:])
        elif kind in ("task", "offer"):
            run["done"] += 1
        elif kind == "site":
            run["pending"].discard(parts[1])
        elif kind == "done":
            run["stage"] = 4
        self._show_progress()

    def _show_progress(self) -> None:
        run = self.run
        if not run or not self.process:
            return
        elapsed = time.monotonic() - run["started"]
        stage, done, total, stages = run["stage"], run["done"], max(1, run["total"]), run["stages"]
        # share of the bar for each step: searching, reading the new offers, checking the old ones
        spans = {1: (0, 45), 2: (45, 80 if stages == 3 else 100), 3: (80, 100)}
        names = {1: _("recherche sur les sites"), 2: _("lecture des offres"), 3: _("vérification des offres")}
        if stage in spans:
            start, end = spans[stage]
            self.progress.configure(value=start + (end - start) * done / total)
            step = _("Étape {number}/{count} : {name} ({done}/{total})").format(
                number=stage, count=stages, name=names[stage], done=done, total=run["total"])
        else:
            step = _("Démarrage…") if stage == 0 else _("Enregistrement…")
        remaining = self._remaining()
        self.status.configure(text=f"{step}   ·   ⏱ {duration(elapsed)}"
                                   + ("   ·   " + _("reste environ {time}").format(time=duration(remaining))
                                      if remaining else ""))

    def _remaining(self) -> float | None:
        """Estimated seconds left: from earlier searches during step 1, from the current speed afterwards."""
        run, history = self.run, self.run["history"]
        in_stage = time.monotonic() - run["stage_started"]
        reads = [r["read_seconds"] for r in history.get("runs", [])[-3:] if "read_seconds" in r]
        reading = sum(reads) / len(reads) if reads else None
        if run["stage"] == 1:
            sites = [history.get("sites", {}).get(name, {}).get("seconds") for name in run["pending"]]
            known = [seconds for seconds in sites if seconds]
            if not known or reading is None:
                return None
            return max(0, max(known) - in_stage) + reading
        if run["stage"] in (2, 3) and run["done"] >= 3:
            return in_stage / run["done"] * (run["total"] - run["done"])
        return None

    def _show_new_offers(self) -> None:
        if any(offer.get("_new") for offer in self.offers):
            self.only_new.set(False)
            self.notebook.select(self.results_tab)

    def _finish(self, code: int) -> None:
        self.process = None
        self._search_button_look("start")
        elapsed = time.monotonic() - self.run.get("started", time.monotonic())
        if code == 0:
            self.progress.configure(value=100)
            self.status.configure(text=_("Terminé en {time}.").format(time=duration(elapsed)))
            self.load_offers(then=self._show_new_offers)
            self._show_last_run()
            self._show_backups()
            if self.root.focus_displayof() is None:  # you are in another window: the taskbar button blinks
                desktop.flash_window(self.root.winfo_id())
        else:
            self.status.configure(text=_("Recherche interrompue après {time} : voir l'onglet Recherche.").format(
                time=duration(elapsed)))
        self.run = {}
