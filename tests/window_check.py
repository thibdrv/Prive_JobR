"""Drives the real window on made-up offers, in the folder given by RETRIEVE_JOB_HOME (see test_window.py).

Opens every tab and sub-tab, checks that .cache/slow.log notes a slow moment, hovers the charts, changes theme and text size, changes a status and a note and
undoes them, and checks that nothing raised an error, that nothing held the window more than a few seconds,
and that the changes reached jobs.xlsx. Prints what went wrong and exits with 1, or exits with 0.
Exit code 77: no screen to open a window on (the test is then skipped).
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
assert os.environ.get("RETRIEVE_JOB_HOME"), "run it through tests/test_window.py: it needs its own folder"

import tkinter as tk  # noqa: E402

try:
    root = tk.Tk()
except tk.TclError:
    sys.exit(77)

import results_file  # noqa: E402
from window import watchdog  # noqa: E402

SLOWEST = 5.0  # seconds a single step may hold the window ("Not responding" comes at about 5)
problems: list[str] = []


def made_up_offers(count: int) -> list[dict]:
    categories, statuses = ["data", "dev", "french / sales / support", "FinTech"], ["", "Postulé", "Entretien",
                                                                                     "Refusé", "Pas intéressé"]
    cities, salaries = ["Limassol", "Nicosia", "Larnaca", "Cyprus"], ["1 500–2 000 €/mois", "", "2 400 €/mois"]
    return [{"Trouvée le": f"2026-11-{1 + number % 28:02d}", "Catégorie": categories[number % 4],
             "Score": str(number % 5), "Titre": f"Offer {number}", "Entreprise": f"Company {number % 7}",
             "Ville": cities[number % 4], "Salaire": salaries[number % 3], "Site": "CyprusJobs",
             "Lien": f"https://example.com/offer/{number}", "Statut": statuses[number % 5],
             "Statut modifié le": "2026-11-20" if number % 5 else "", "Compétences": "python, sql",
             "Description": f"Offer {number}: python and sql, in Limassol."} for number in range(count)]


def step(name: str, action) -> None:
    started = time.perf_counter()
    try:
        action()
        root.update()
    except Exception as error:  # noqa: BLE001 - every failure is reported
        problems.append(f"{name}: {type(error).__name__}: {error}")
        return
    seconds = time.perf_counter() - started
    if seconds > SLOWEST:
        problems.append(f"{name}: held the window {seconds:.1f} s")


def wait_for(condition, seconds: float = 30) -> bool:
    end = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > end:
            return False
        root.update()
        time.sleep(0.02)
    return True


def in_file(link: str, header: str) -> str:
    return next(offer.get(header, "") for offer in results_file.read_rows() if offer["Lien"] == link)


def hover_charts(app) -> None:
    """Moves the pointer over each bar: the tooltip must show and never sit under the pointer."""
    for page in range(len(app.stats.pages.tabs())):
        app.stats.pages.select(page)
        root.update()
        for _key, _title, canvas in app.stats.charts:
            if not canvas.winfo_ismapped():
                continue
            for item in canvas.find_all():
                if canvas.type(item) != "rectangle" or "tooltip" in canvas.gettags(item):
                    continue
                x0, y0, x1, y1 = canvas.coords(item)
                x, y = int(x1 - 2), int((y0 + y1) / 2)
                canvas.event_generate("<Motion>", x=x, y=y)
                root.update()
                tips = canvas.find_withtag("tooltip")
                if tips:
                    bx0, by0, bx1, by1 = canvas.bbox(*tips)
                    if bx0 <= x <= bx1 and by0 <= y <= by1:
                        problems.append("a tooltip sits under the pointer (it would flicker without end)")
                        return
                canvas.event_generate("<Leave>")
                root.update()


def main() -> None:
    offers = made_up_offers(60)
    results_file.write(offers[:8], offers[8:], ["data", "dev"])
    import app as app_module
    app_module.App._prepare = lambda self: self.messages.put(("ready", None))  # nothing to install here
    root.geometry("1150x780")
    app = app_module.App(root)
    if not wait_for(lambda: app.ready and app.loads and app.loaded == app.loads):
        problems.append("the offers never showed in the table")
        return
    if len(app.table.get_children()) != 60:
        problems.append(f"{len(app.table.get_children())} rows in the table, 60 expected")

    def hold_the_window():  # a slow moment on purpose: slow.log must note it, with this function
        time.sleep(0.8)
    root.after(10, hold_the_window)
    end = time.monotonic() + 1.5
    while time.monotonic() < end:
        root.update()
        time.sleep(0.02)
    slow = watchdog.SLOW_LOG.read_text(encoding="utf-8") if watchdog.SLOW_LOG.exists() else ""
    if "start:" not in slow:
        problems.append("slow.log does not give the start time")
    if "hold_the_window" not in slow:
        problems.append("slow.log missed a 0.8 s hold of the window. It holds: " + slow)

    for index in range(len(app.notebook.tabs())):
        step(f"tab {app.notebook.tab(index, 'text')}", lambda i=index: app.notebook.select(i))
    if not any(isinstance(child, tk.Widget) for child in app.notebook.nametowidget(app.notebook.select()).winfo_children()):
        problems.append("the Information tab is empty")
    app.notebook.select(1)
    step("hovering the charts", lambda: hover_charts(app))

    for theme in ("dark", "light"):
        app.theme_var.set(theme)
        step(f"theme {theme}", app.change_theme)
    for size in ("xlarge", "normal"):
        app.text_var.set(size)
        step(f"text size {size}", app.change_display)

    app.notebook.select(0)
    root.update()
    first = app.table.get_children()[0]
    link = app.offers[int(first)]["Lien"]
    app.table.selection_set(first)
    step("changing a status", lambda: app.set_status("Entretien"))
    if app.offers[int(first)].get("Statut") != "Entretien":
        problems.append("the status did not change in the table")
    app.notes.set("call back on Monday")
    step("saving a note", app.save_notes)
    if not app.files.wait(30):
        problems.append("the changes were still not saved after 30 s")
    if in_file(link, "Statut") != "Entretien" or in_file(link, "Notes") != "call back on Monday":
        problems.append("the status or the note did not reach jobs.xlsx")
    step("undo", app.undo)
    step("undo", app.undo)
    app.files.wait(30)
    if in_file(link, "Notes") or in_file(link, "Statut") == "Entretien":
        problems.append("undo did not put back the file as it was")
    step("reading the file again (F5)", app.load_offers)
    wait_for(lambda: app.loaded == app.loads)
    for name in ("jobs.saving.xlsx",):
        if (results_file.RESULTS / name).exists():
            problems.append(f"{name} was left behind")


try:
    main()
finally:
    if watchdog.ERROR_LOG.exists():
        problems.append("errors in .cache/errors.log:\n" + watchdog.ERROR_LOG.read_text(encoding="utf-8"))
    if watchdog.FREEZE_LOG.exists():
        problems.append("freezes in .cache/freeze.log:\n" + watchdog.FREEZE_LOG.read_text(encoding="utf-8"))
    try:
        root.destroy()
    except tk.TclError:
        pass
print("\n".join(problems) or "OK")
sys.exit(1 if problems else 0)
