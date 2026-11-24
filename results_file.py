"""results/jobs.xlsx: reading it back, writing it after a search, and changing offers from the app.

Inside the app, columns and values have their French names. The file is written in the chosen language
(i18n) and read back in either one.
Next to it, in .cache: the offers' descriptions (shown in the app), when each was last found online, and a quick
copy of the offers as the app reads them (offers.json), used while jobs.xlsx has not changed since.
"""
import json
import shutil
import threading
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from i18n import _, to_french, value
from settings import APP_DIR, replace_file, write_safely

RESULTS = APP_DIR / "results"
EXCEL_FILE = RESULTS / "jobs.xlsx"
BACKUPS = RESULTS / "backups"  # copies of jobs.xlsx: jobs_2026-11-23_09-30-00.xlsx
CACHE = APP_DIR / ".cache"
DESCRIPTIONS_FILE = CACHE / "descriptions.json"  # link -> text of the offer
ONLINE_FILE = CACHE / "online_checks.json"  # link -> date it was last checked
# The same details as in the app: everything you can filter or sort there, you can in Excel too
COLUMNS = [("Trouvée le", 12), ("Nouvelle", 10), ("Catégorie", 24), ("Score", 8), ("Titre", 55), ("Entreprise", 28),
           ("Ville", 22), ("Publiée", 12), ("Expérience", 13), ("Contrat", 15), ("Mode de travail", 15),
           ("Salaire", 20), ("Compétences", 30), ("Site", 14), ("Trouvée par", 20), ("Lien", 50), ("Statut", 18),
           ("Statut modifié le", 14), ("Notes", 40), ("En ligne", 11), ("Vérifiée le", 12), ("Description", 80)]
HEADERS = [header for header, _width in COLUMNS]
TRANSLATED = {"Nouvelle", "Catégorie", "Expérience", "Contrat", "Mode de travail", "Salaire", "Statut", "En ligne"}
DESCRIPTION_LENGTH = 30000  # an Excel cell holds at most 32,767 characters
NEW_OFFER_COLOR = "FFFF00"  # yellow: found by the latest search
EXPIRED_COLOR = "9A9A9A"  # grey and struck through: no longer online
# Pale colours for the Catégorie cell, one per category, in the order of the settings
CATEGORY_COLORS = ["DDEBF7", "E2EFDA", "FCE4D6", "EDE1F5", "D9F2F2", "FFF2CC", "F8D7DA", "E7E6E6"]
STATUSES = ["À voir", "Postulé", "Entretien", "Refusé", "Pas intéressé"]
ONLINE, EXPIRED = "oui", "expirée"  # values of the En ligne column; empty = not checked yet
SHEETS = ("Offres", "Résumé")
# One change of the file at a time inside the app (status, note, description, restore)
FILE_LOCK = threading.RLock()


# ---- openpyxl, loaded only when jobs.xlsx is really read or written ----
# Loading it takes 0.4 s: the app shows the offers from their quick copy without it.

def load_workbook(path):
    from openpyxl import load_workbook as load
    return load(path)


def Workbook():  # noqa: N802 - the names of openpyxl
    from openpyxl import Workbook as new
    return new()


def Font(**style):  # noqa: N802
    from openpyxl.styles import Font as font
    return font(**style)


def PatternFill(fill_type: str, start_color: str):  # noqa: N802
    from openpyxl.styles import PatternFill as fill
    return fill(fill_type, start_color=start_color)


def Alignment(**style):  # noqa: N802
    from openpyxl.styles import Alignment as alignment
    return alignment(**style)


def get_column_letter(number: int) -> str:
    from openpyxl.utils import get_column_letter as letter
    return letter(number)


def is_locked() -> bool:
    """True when another program (Excel) keeps the file locked, so saving would fail."""
    try:
        if EXCEL_FILE.exists():
            EXCEL_FILE.open("a").close()
        return False
    except PermissionError:
        return True


def _offers_sheet(workbook):
    for name in (SHEETS[0], _(SHEETS[0]), "Offers"):
        if name in workbook.sheetnames:
            return workbook[name]
    return workbook.active


def _headers(sheet) -> list[str]:
    return [to_french(str(cell.value)) if cell.value is not None else "" for cell in sheet[1]]


QUICK_COPY_FORMAT = 1  # goes up if what read_rows gives changes, so an older copy is not used


def _quick_copy_file() -> Path:
    return CACHE / "offers.json"


def _stamp() -> list[int]:
    """What changes whenever jobs.xlsx is written (by the app, a search, Excel, a restored copy)."""
    state = EXCEL_FILE.stat()
    return [state.st_mtime_ns, state.st_size]


def read_rows(with_new: bool = False) -> list[dict]:
    """The offers in jobs.xlsx, in the order they are now (you may have sorted them).

    with_new adds "_new": True for the offers the latest search found (the yellow ones). That is how the app reads
    them: from the quick copy while jobs.xlsx has not changed since it was made (reading Excel takes 0.5 s for
    300 offers, the copy 0.01 s); otherwise from jobs.xlsx, and the copy is made again.
    """
    if not EXCEL_FILE.exists():
        return []
    if with_new:
        stamp = _stamp()
        copy = _load(_quick_copy_file())
        if copy.get("format") == QUICK_COPY_FORMAT and copy.get("stamp") == stamp:
            return copy["rows"]
        rows = _read_excel(with_new=True)
        try:
            _save(_quick_copy_file(), {"format": QUICK_COPY_FORMAT, "stamp": stamp, "rows": rows})
        except OSError:
            pass  # only slower next time
        return rows
    return _read_excel(with_new=False)


def _read_excel(with_new: bool) -> list[dict]:
    sheet = _offers_sheet(load_workbook(EXCEL_FILE))
    headers = _headers(sheet)
    if "Lien" not in headers:  # a file from an older version of the app: it gets replaced
        return []
    offers = []
    for cells in sheet.iter_rows(min_row=2):
        if all(cell.value is None for cell in cells):
            continue
        offer = {h: ("" if cell.value is None else str(cell.value)) for h, cell in zip(headers, cells)}
        for header in TRANSLATED & offer.keys():
            offer[header] = to_french(offer[header])
        if with_new:
            offer["_new"] = str(cells[0].fill.start_color.rgb or "").upper().endswith("FFFF00")
        offers.append(offer)
    return offers


def write(new_rows: list[dict], old_rows: list[dict], category_order: list[str]) -> None:
    """Writes the file: this search's offers on top in yellow, then the older ones, plus a summary sheet."""
    colors = _category_colors(category_order, new_rows + old_rows)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = _(SHEETS[0])
    sheet.append([_(header) for header in HEADERS])
    for cell, (_header, width) in zip(sheet[1], COLUMNS):
        cell.font = Font(bold=True)
        sheet.column_dimensions[cell.column_letter].width = width
    link_column = HEADERS.index("Lien") + 1
    category_column = HEADERS.index("Catégorie") + 1
    for number, row in enumerate(new_rows + old_rows):
        row["Nouvelle"] = "oui" if number < len(new_rows) else "non"
        row["Description"] = (row.get("Description") or "")[:DESCRIPTION_LENGTH]
        sheet.append([_cell_value(header, row.get(header, "")) for header in HEADERS])
        line = sheet.max_row
        if row.get("Lien"):
            link = sheet.cell(row=line, column=link_column)
            link.hyperlink = row["Lien"]
            link.style = "Hyperlink"
        if number < len(new_rows):  # this run's offers stand out; older ones lose the highlight
            for cell in sheet[line]:
                cell.fill = PatternFill("solid", start_color=NEW_OFFER_COLOR)
        elif row.get("En ligne") == EXPIRED:
            for cell in sheet[line]:
                if cell.column != link_column:
                    cell.font = Font(color=EXPIRED_COLOR, strike=True)
        color = colors.get(row.get("Catégorie", ""))
        if color:
            sheet.cell(row=line, column=category_column).fill = PatternFill("solid", start_color=color)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    _write_summary(workbook.create_sheet(_(SHEETS[1])), new_rows + old_rows, len(new_rows), colors)
    _save_workbook(workbook)


def _save_workbook(workbook) -> None:
    """Saves jobs.xlsx next to itself first, then puts it in place: never a half-written file.
    PermissionError when Excel holds the file."""
    RESULTS.mkdir(exist_ok=True)
    temporary = RESULTS / "jobs.saving.xlsx"
    workbook.save(temporary)
    replace_file(temporary, EXCEL_FILE)


def set_field(links: list[str], header: str, text: str) -> int:
    """Writes text in one column (Statut, Notes, Description) of these offers, keeping everything else.

    Changing the Statut also writes the date in "Statut modifié le". Returns how many offers changed.
    """
    values = {header: text}
    if header == "Statut":
        values["Statut modifié le"] = date.today().isoformat() if text else ""
    with FILE_LOCK:
        return _set_values(links, values)


def _set_values(links: list[str], values: dict[str, str]) -> int:
    before = _stamp()
    workbook = load_workbook(EXCEL_FILE)
    sheet = _offers_sheet(workbook)
    headers = _headers(sheet)
    for name in values:
        if name not in headers:  # a file written before this column existed
            sheet.cell(row=1, column=len(headers) + 1).value = _(name)
            sheet.cell(row=1, column=len(headers) + 1).font = Font(bold=True)
            headers.append(name)
    link_column = headers.index("Lien") + 1
    wanted = set(links)
    changed = 0
    for line in range(2, sheet.max_row + 1):
        if sheet.cell(row=line, column=link_column).value in wanted:
            for name, new in values.items():
                if name == "Description":
                    new = new[:DESCRIPTION_LENGTH]
                sheet.cell(row=line, column=headers.index(name) + 1).value = _cell_value(name, new) or None
            changed += 1
    _save_workbook(workbook)
    _update_quick_copy(before, wanted, values)
    return changed


def _update_quick_copy(before: list[int], links: set[str], values: dict[str, str]) -> None:
    """The same change in the quick copy, so the next reading stays quick; dropped if it was already out of date."""
    path = _quick_copy_file()
    copy = _load(path)
    if copy.get("format") != QUICK_COPY_FORMAT or copy.get("stamp") != before:
        path.unlink(missing_ok=True)
        return
    for row in copy["rows"]:
        if row.get("Lien") in links:
            for name, new in values.items():
                row[name] = new[:DESCRIPTION_LENGTH] if name == "Description" else new
    copy["stamp"] = _stamp()
    try:
        _save(path, copy)
    except OSError:
        path.unlink(missing_ok=True)


def set_status(links: list[str], status: str) -> int:
    return set_field(links, "Statut", status)


# ---- backups ----

def backup(keep: int) -> Path | None:
    """Copies jobs.xlsx into results/backups and keeps only the `keep` newest copies; None when there is nothing to copy."""
    if keep <= 0 or not EXCEL_FILE.exists():
        return None
    BACKUPS.mkdir(parents=True, exist_ok=True)
    copy = BACKUPS / f"jobs_{datetime.now():%Y-%m-%d_%H-%M-%S}.xlsx"
    shutil.copy2(EXCEL_FILE, copy)
    for old in backups()[keep:]:
        old.unlink(missing_ok=True)
    return copy


def backups() -> list[Path]:
    """The copies of jobs.xlsx, newest first."""
    return sorted(BACKUPS.glob("jobs_*.xlsx"), reverse=True) if BACKUPS.exists() else []


def restore(copy: Path, keep: int) -> None:
    """Puts a copy back as jobs.xlsx. The current file is copied first, so a restore can be undone."""
    with FILE_LOCK:
        if is_locked():
            raise PermissionError(EXCEL_FILE)
        backup(max(keep, 1) + 1)
        temporary = RESULTS / "jobs.saving.xlsx"
        shutil.copy2(copy, temporary)
        replace_file(temporary, EXCEL_FILE)


# ---- what is kept next to the file ----

def _load(path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(path, data: dict) -> None:
    write_safely(path, json.dumps(data, ensure_ascii=False))


def descriptions() -> dict[str, str]:
    return _load(DESCRIPTIONS_FILE)


def save_descriptions(new: dict[str, str], keep: set[str] | None = None) -> None:
    """Adds descriptions; with keep, also forgets those of offers no longer in the file."""
    with FILE_LOCK:
        _add_descriptions(new, keep)


def _add_descriptions(new: dict[str, str], keep: set[str] | None) -> None:
    data = descriptions()
    data.update({link: text[:20000] for link, text in new.items() if text})
    if keep is not None:
        data = {link: text for link, text in data.items() if link in keep}
    _save(DESCRIPTIONS_FILE, data)


def online_checks() -> dict[str, str]:
    return _load(ONLINE_FILE)


def save_online_checks(data: dict[str, str]) -> None:
    _save(ONLINE_FILE, data)


# ---- writing helpers ----

def _cell_value(header: str, text):
    if header == "Score" and isinstance(text, str) and text.isdigit():
        return int(text)  # a number, so that sorting by score works
    if header in TRANSLATED and isinstance(text, str):
        return value(text)
    return text


def category_order(order: list[str], rows: list[dict]) -> list[str]:
    """The categories in colour order: your job types first, then the others alphabetically (the app uses it too)."""
    return list(dict.fromkeys(order + sorted({row.get("Catégorie", "") for row in rows} - {""})))


def _category_colors(order: list[str], rows: list[dict]) -> dict[str, str]:
    return {name: CATEGORY_COLORS[index % len(CATEGORY_COLORS)]
            for index, name in enumerate(category_order(order, rows))}


def _write_summary(sheet, rows: list[dict], new_count: int, colors: dict[str, str]) -> None:
    """Counts by category, site, status and week. Category, site and status counts are formulas,
    so they follow the changes you make in the offers sheet."""
    bold = Font(bold=True)
    offers = _(SHEETS[0])
    sheet.column_dimensions["A"].width = 34
    sheet.column_dimensions["B"].width = 12
    sheet.append([_("Résumé des offres"), ""])
    sheet["A1"].font = Font(bold=True, size=14)
    sheet.append([_("Mis à jour le {date}").format(date=date.today().isoformat()), ""])
    sheet.append([_("Offres dans le fichier"), f"=COUNTA('{offers}'!A:A)-1"])
    sheet.append([_("Nouvelles à la dernière recherche"), new_count])
    sheet["B4"].fill = PatternFill("solid", start_color=NEW_OFFER_COLOR)
    sheet.append([_("Expirées"), sum(1 for row in rows if row.get("En ligne") == EXPIRED)])

    def column(header: str) -> str:
        letter = get_column_letter(HEADERS.index(header) + 1)
        return f"'{offers}'!${letter}:${letter}"

    def section(title: str, header: str, values: list[str]) -> None:
        sheet.append([])
        sheet.append([_(title), _("Offres")])
        for cell in sheet[sheet.max_row]:
            cell.font = bold
        for name in values:
            shown = _cell_value(header, name)
            sheet.append([shown, f'=COUNTIF({column(header)},"{shown}")'])
            if header == "Catégorie" and name in colors:
                sheet.cell(row=sheet.max_row, column=1).fill = PatternFill("solid", start_color=colors[name])

    section("Par catégorie", "Catégorie", [name for name in colors if any(r.get("Catégorie") == name for r in rows)])
    section("Par site", "Site", sorted({row.get("Site", "") for row in rows} - {""}))
    section("Par statut", "Statut", STATUSES + sorted({row.get("Statut", "") for row in rows} - set(STATUSES) - {""}))
    sheet.append([_("Sans statut"), f'=COUNTA({column("Lien")})-COUNTA({column("Statut")})'])  # both count the header

    weeks = Counter()
    for row in rows:
        try:
            year, week, _day = date.fromisoformat(row.get("Trouvée le", "")[:10]).isocalendar()
            weeks[_("{year} - semaine {week:02d}").format(year=year, week=week)] += 1
        except ValueError:
            pass
    sheet.append([])
    sheet.append([_("Trouvées par semaine"), _("Offres")])
    for cell in sheet[sheet.max_row]:
        cell.font = bold
    for week, count in sorted(weeks.items(), reverse=True):
        sheet.append([week, count])
    for line in sheet.iter_rows(min_col=2, max_col=2):
        line[0].alignment = Alignment(horizontal="right")
