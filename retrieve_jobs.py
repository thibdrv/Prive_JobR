"""Find job offers on several sites and keep the ones that fit in results/jobs.xlsx.

The settings come from settings.json, edited in the app window (python app.py).
jobs.xlsx holds every offer kept so far, newest first, with its category, details and link,
plus Statut and Notes columns for you. Offers already looked at are never added twice.
Each search also checks that the offers already in the file are still online.

Run it from the app, or: python retrieve_jobs.py [--open]
"""
import argparse
import csv
import json
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlsplit

import desktop
import results_file
import settings as app_settings
from experience import (JUNIOR_WORDS, contract_type, requires_language, salary_range, salary_text, skills_found,
                        work_mode, years_required)
from i18n import _, set_language
from settings import APP_DIR, write_safely
from sources import BROWSE_SOURCES, COMPANY_SOURCE, REMOTE_SOURCES, SOURCES, company_jobs
from sources.common import Job, Settings, canonical_url, check_online, has_word, new_session, page_text

CACHE = APP_DIR / ".cache"
CHECKED_FILE = CACHE / "checked_links.txt"  # every offer already looked at, kept or not
HISTORY_FILE = CACHE / "history.json"  # how long each site took and how many offers it gave, for estimates
LOG_FILE = CACHE / "last_run.log"  # what a search started without a window (daily task) printed
FOLLOWED = "Entreprises suivies"  # category of a followed company's offer that fits no job type
CHECK_EVERY_DAYS = 3  # an offer already in the file is checked online at most this often


@dataclass
class Filters:
    """What stage 2 checks in each offer's text."""
    max_years: int
    languages: list[str]
    required_words: list[str]
    forbidden_words: list[str]
    skills: list[str]
    contracts: set[str]  # accepted, from settings.CONTRACTS
    work_modes: set[str]  # accepted, from settings.WORK_MODES
    min_salary: int  # € gross per month, 0 = any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find job offers on several job sites.")
    parser.add_argument("--open", action="store_true", help="open jobs.xlsx when done")
    parser.add_argument("--progress", action="store_true", help="print progress lines for the app window")
    args = parser.parse_args(argv)
    _setup_output()
    global _progress_lines
    _progress_lines = args.progress
    started = time.monotonic()

    config = app_settings.load()
    set_language(config["language"])
    settings = Settings(
        max_pages=max(1, int(config["max_pages"])),
        max_age_days=int(config["max_age_days"]),
        remote_locations=config["remote_locations"],
        careerfinders_categories=[(name, app_settings.CAREERFINDERS_CATEGORIES[name])
                                  for name in config["careerfinders_categories"]
                                  if name in app_settings.CAREERFINDERS_CATEGORIES],
        companies=[c for c in config["companies"]
                   if c.get("id", "").strip() and c.get("platform") in app_settings.COMPANY_PLATFORMS.values()],
        cities=config["cities"],
    )
    categories = {cat["name"]: cat["title_words"] for cat in config["categories"] if cat["name"].strip()}
    searches = list(dict.fromkeys(s for cat in config["categories"] for s in cat["searches"] if s.strip()))
    excluded = config["seniority_words"] + config["exclude_words"]
    enabled = [name for name, on in config["sources"].items()
               if on and (name in SOURCES or name in BROWSE_SOURCES or (name == COMPANY_SOURCE and settings.companies))]
    if not enabled or (not searches and all(name in SOURCES for name in enabled)):
        print(_("Rien à chercher : ajoute au moins un type de poste avec une recherche, et coche au moins un site."))
        return 1
    if results_file.is_locked():
        print(_("Ferme {file} dans Excel, puis relance la recherche.").format(file=results_file.EXCEL_FILE.name))
        return 1

    copy = results_file.backup(int(config["backups_to_keep"]))
    if copy:
        print(_("Sauvegarde de {file} : {copy}").format(file=results_file.EXCEL_FILE.name, copy=copy.name) + "\n")
    old_rows, expired = _drop_expired(results_file.read_rows(), int(config["keep_found_days"]))
    seen = _checked_links() | {canonical_url(row["Lien"]) for row in old_rows if row.get("Lien")}
    seen |= _job_agent_links(config["job_agent_folder"])
    seen_offers = {_offer_key(row.get("Titre", ""), row.get("Entreprise", "")) for row in old_rows} - {""}
    history = _load_history()
    candidates: list[Job] = []
    failed: list[str] = []
    warnings: list[str] = []
    duplicates = 0

    tasks = {name: _tasks(name, searches, settings) for name in enabled}
    print(_("1. Recherche des offres sur {count} sites en même temps").format(count=len(enabled)) + "\n")
    _event("stage", 1, sum(len(t) for t in tasks.values()), *enabled)
    stage_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(enabled)) as pool:
        futures = {pool.submit(_search_site, name, tasks[name]): name for name in enabled}
        for future in as_completed(futures):
            name = futures[future]
            seconds = time.monotonic() - stage_started
            found_count = kept = errors = 0
            for search, found in future.result():
                if isinstance(found, Exception):  # one broken site or search must not stop the others
                    failed.append(f"{name} / {search}")
                    errors += 1
                    continue
                found_count += len(found)
                for job in found:
                    job.url = canonical_url(job.url)
                    job.category = _category(job.title, categories)
                    if name in BROWSE_SOURCES:
                        job.category = job.category or job.search  # else the site's own category, e.g. "Forex"
                    elif name == COMPANY_SOURCE:
                        job.category = job.category or (FOLLOWED if config["companies_keep_all"] else "")
                    else:
                        job.search = search
                    if (job.url in seen or not job.category
                            or any(_has_whole_word(job.title, word) for word in excluded)
                            or any(_has_whole_word(job.company, word) for word in config["excluded_companies"])
                            or (name != COMPANY_SOURCE  # their "Limassol; Yerevan" means either city
                                and any(_has_whole_word(job.location, place) for place in config["excluded_places"]))
                            or _too_old(job.posted, settings.max_age_days)
                            or (name not in REMOTE_SOURCES and not _in_area(job.location, config["cities"]))):
                        continue
                    seen.add(job.url)
                    key = _offer_key(job.title, job.company)
                    if key and key in seen_offers:  # the same offer, already found on another site
                        duplicates += 1
                        continue
                    seen_offers.add(key)
                    candidates.append(job)
                    kept += 1
            _say("  => " + _("{site} terminé en {time} : {read} offres lues, {kept} nouvelles qui correspondent").format(
                site=name, time=_duration(seconds), read=found_count, kept=kept))
            _event("site", name, round(seconds))
            warning = _site_warning(name, found_count, errors, len(tasks[name]), history)
            if warning:
                warnings.append(warning)
            if not errors:
                history["sites"][name] = {"seconds": round(seconds), "found": found_count}
    stage1_seconds = time.monotonic() - stage_started

    filters = Filters(
        max_years=int(config["max_experience_years"]),
        languages=[lang for lang in config["excluded_languages"] if lang.strip()],
        required_words=[w for w in config["required_words"] if w.strip()],
        forbidden_words=[w for w in config["forbidden_words"] if w.strip()],
        skills=config["skills"],
        contracts={name for name, on in config["contracts"].items() if on},
        work_modes={name for name, on in config["work_modes"].items() if on},
        min_salary=int(config["min_salary"] or 0),
    )
    print("\n" + _("2. Lecture des offres : expérience demandée ({years} ans maximum)").format(years=filters.max_years)
          + (_(", langues exigées ({languages})").format(languages=", ".join(filters.languages))
             if filters.languages else "")
          + _(", contrat, salaire et compétences, pour {count} offre(s)").format(count=len(candidates)) + "\n")
    _event("stage", 2, len(candidates))
    stage_started = time.monotonic()
    by_site: dict[str, list[Job]] = {}
    for job in candidates:
        by_site.setdefault(job.source, []).append(job)
    progress = _Progress(len(candidates))
    with ThreadPoolExecutor(max_workers=max(1, len(by_site))) as pool:
        results = [result for site_results in pool.map(
            lambda jobs: _read_offers(jobs, filters, progress), by_site.values())
            for result in site_results]
    kept_jobs = [job for job, reason in results if not reason]
    kept_jobs.sort(key=candidates.index)  # back in the order they were found
    rejected = Counter(reason for _job, reason in results if reason)
    checked = [job.url for job, _reason in results if job.experience != "page non lue"]  # failed pages: retried
    print("  " + _("{count} gardées").format(count=len(kept_jobs))
          + "".join(", " + _("{count} écartées ({reason})").format(count=count, reason=_(reason))
                    for reason, count in rejected.most_common()))
    read_seconds = time.monotonic() - stage_started

    gone, online_checks = _check_still_online(old_rows) if config["check_online"] else (0, None)
    known = results_file.descriptions()  # offers found before the Description column existed
    for row in old_rows:
        row["Description"] = row.get("Description") or known.get(row.get("Lien", ""), "")

    try:
        results_file.write([_row(job) for job in kept_jobs], old_rows, list(categories))
    except PermissionError:
        print("\n" + _("Rien n'a été enregistré : {file} a été ouvert pendant la recherche. Ferme-le et relance.")
              .format(file=results_file.EXCEL_FILE.name))
        return 1
    CACHE.mkdir(exist_ok=True)
    with CHECKED_FILE.open("a", encoding="utf-8") as f:
        f.writelines(f"{url}\n" for url in checked)
    if online_checks is not None:
        results_file.save_online_checks(online_checks)
    results_file.save_descriptions({job.url: job.description for job in kept_jobs},
                                   keep={job.url for job in kept_jobs} | {row.get("Lien") for row in old_rows})

    total_seconds = time.monotonic() - started
    print("\n" + _("{count} nouvelle(s) offre(s) ajoutée(s) dans {file}").format(
        count=len(kept_jobs), file=results_file.EXCEL_FILE))
    for category, count in Counter(job.category for job in kept_jobs).most_common():
        print(f"  {_(category)} : {count}")
    if duplicates:
        print(_("{count} offre(s) en double (même poste, même entreprise sur un autre site) ignorée(s)").format(
            count=duplicates))
    if gone:
        print(_("{count} offre(s) du fichier ne sont plus en ligne : marquées « expirée »").format(count=gone))
    if expired:
        print(_("{count} offre(s) trouvée(s) il y a plus de {days} jours retirée(s) du fichier").format(
            count=expired, days=config["keep_found_days"]))
    if failed:
        print(_("{count} recherche(s) en erreur : {list}").format(count=len(failed), list=", ".join(failed)))
    for warning in warnings:
        print(_("Attention : {warning}").format(warning=warning))
    print("\n" + _("Terminé en {time}.").format(time=_duration(total_seconds)))

    history["runs"] = (history["runs"] + [{
        "date": datetime.now().isoformat(timespec="minutes"), "seconds": round(total_seconds),
        "search_seconds": round(stage1_seconds), "read_seconds": round(read_seconds),
        "offers_read": len(candidates), "kept": len(kept_jobs)}])[-20:]
    _save_history(history)
    _event("done", round(total_seconds), len(kept_jobs))
    if config["notify"]:
        desktop.notify("Retrieve Job", _("{count} nouvelle(s) offre(s) trouvée(s)").format(count=len(kept_jobs))
                       if kept_jobs else _("Recherche terminée : pas de nouvelle offre"))
    if args.open and results_file.EXCEL_FILE.exists():
        desktop.open_file(results_file.EXCEL_FILE)
    return 0


# ---- progress and timing ----

_print_lock = threading.Lock()
_progress_lines = False


def _say(text: str) -> None:
    """print() that several sites can use at once without mixing their lines."""
    with _print_lock:
        print(text)


def _event(*parts) -> None:
    """A line for the app window's progress bar ("@@ stage 2 45"); nothing when run alone."""
    if _progress_lines:
        _say("@@ " + " ".join(str(part) for part in parts))


def _duration(seconds: float) -> str:
    minutes, seconds = divmod(round(seconds), 60)
    return f"{minutes} min {seconds:02d} s" if minutes else f"{seconds} s"


def _setup_output() -> None:
    if sys.stdout is None:  # started without a window (daily task): what it says goes to a log file
        CACHE.mkdir(exist_ok=True)
        sys.stdout = sys.stderr = LOG_FILE.open("w", encoding="utf-8", buffering=1)
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _load_history() -> dict:
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {}
    return {"sites": history.get("sites", {}), "runs": history.get("runs", [])}


def _save_history(history: dict) -> None:
    write_safely(HISTORY_FILE, json.dumps(history, indent=1, ensure_ascii=False))


def _site_warning(name: str, found: int, errors: int, tasks: int, history: dict) -> str:
    """A message when a site seems broken: it never answered, or it gave nothing while it used to."""
    if tasks and errors == tasks:
        return _("{site} n'a répondu à aucune recherche (site en panne, ou il bloque l'application).").format(site=name)
    if not errors and not found and history["sites"].get(name, {}).get("found", 0) > 0:
        return _("{site} n'a renvoyé aucune offre alors qu'il en donnait la dernière fois : il a peut-être changé "
                 "sa présentation (son code est dans le dossier sources).").format(site=name)
    return ""


# ---- stage 1: searching ----

def _tasks(name: str, searches: list[str], settings: Settings) -> list[tuple[str, object]]:
    """What to ask one site: (label, function of a session returning its offers)."""
    if name in BROWSE_SOURCES:
        return [(_("toutes ses offres"), lambda session: BROWSE_SOURCES[name](session, settings))]
    if name == COMPANY_SOURCE:
        return [(company["name"], lambda session, c=company: company_jobs(session, c, settings))
                for company in settings.companies]
    return [(search, lambda session, s=search: SOURCES[name](session, s, settings)) for search in searches]


def _search_site(name: str, tasks: list[tuple[str, object]]) -> list[tuple[str, list[Job] | Exception]]:
    """Every search on one site, one after the other, with its own connection (sites run side by side)."""
    session = new_session()
    results = []
    for label, task in tasks:
        try:
            found = task(session)
            _say(f"  {name} / {label} : " + _("{count} offres").format(count=len(found)))
        except Exception as exc:
            found = exc
            _say(f"  {name} / {label} : " + _("erreur, ignoré ({error})").format(error=exc))
        results.append((label, found))
        _event("task", name)
    return results


# ---- stage 3: are the offers already in the file still online? ----

def _check_still_online(rows: list[dict]) -> tuple[int, dict[str, str]]:
    """Marks the file's offers that were removed from their site.

    Returns how many are newly expired, and the dates of the checks (saved once the file is written).

    Each offer is checked at most every CHECK_EVERY_DAYS days, the sites side by side, one page at a time each.
    """
    checks = results_file.online_checks()
    today = date.today()
    due = []
    for row in rows:
        if not row.get("Lien") or row.get("En ligne") == results_file.EXPIRED:
            continue
        try:
            fresh = (today - date.fromisoformat(checks.get(row["Lien"], ""))).days < CHECK_EVERY_DAYS
        except ValueError:
            fresh = False
        if not fresh:
            due.append(row)
    print("\n" + _("3. Vérification des offres déjà trouvées : sont-elles encore en ligne ? ({count} à vérifier)")
          .format(count=len(due)) + "\n")
    _event("stage", 3, len(due))
    by_site: dict[str, list[dict]] = {}
    for row in due:
        by_site.setdefault(urlsplit(row["Lien"]).netloc, []).append(row)
    progress = _Progress(len(due), _("vérifiées"))

    def check_site(site_rows: list[dict]) -> int:
        session = new_session()
        gone = 0
        for row in site_rows:
            online = check_online(session, row["Lien"])
            if online is not None:
                row["En ligne"] = results_file.ONLINE if online else results_file.EXPIRED
                row["Vérifiée le"] = checks[row["Lien"]] = today.isoformat()
                gone += not online
            progress.step()
        return gone

    with ThreadPoolExecutor(max_workers=max(1, min(16, len(by_site)))) as pool:
        gone = sum(pool.map(check_site, by_site.values()))
    known = {row.get("Lien") for row in rows}
    print("  " + _("{count} plus en ligne").format(count=gone))
    return gone, {link: day for link, day in checks.items() if link in known}


def _category(title: str, categories: dict[str, list[str]]) -> str:
    """The first category with a word in the title, or "" when none fits."""
    return next((name for name, words in categories.items()
                 if any(has_word(title, word) for word in words)), "")


def _has_whole_word(text: str, word: str) -> bool:
    return bool(word.strip()) and re.search(rf"\b{re.escape(word.strip())}\b", text, re.IGNORECASE) is not None


def _in_area(location: str, cities: list[str]) -> bool:
    """True for offers in one of the cities, or that only say "Cyprus" (the city could be one of them)."""
    if not cities or any(has_word(location, city) for city in cities):
        return True
    rest = re.sub(r"(?i)\b(republic of|cyprus|remote|hybrid)\b", "", location)
    return not re.sub(r"[\W_]+", "", rest)


def _offer_key(title: str, company: str) -> str:
    """Same title at the same company = the same offer, whatever the site. "" when it can't be told."""
    company = re.sub(r"\b(ltd|limited|llc|plc|inc|group|holdings?|cyprus|cy)\b", " ", company.lower())
    company = " ".join(re.findall(r"\w+", company))
    if not company or "pour un client" in company:  # recruiters hide the employer: two offers may share a title
        return ""
    return " ".join(re.findall(r"\w+", title.lower())) + " @ " + company


def _too_old(posted: str, max_age_days: int) -> bool:
    age = _age_in_days(posted)
    return bool(max_age_days and age is not None and age > max_age_days)


def _age_in_days(posted: str) -> int | None:
    """Days since posting, from "2026-10-20" or "2 weeks ago"; None when unknown."""
    posted = posted.lower()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", posted):
        return (date.today() - date.fromisoformat(posted)).days
    if "today" in posted or "hour" in posted or "minute" in posted:
        return 0
    if "yesterday" in posted:
        return 1
    match = re.search(r"(\d+)\s*(day|week|month|year)", posted)
    if match:
        return int(match.group(1)) * {"day": 1, "week": 7, "month": 30, "year": 365}[match.group(2)]
    if re.search(r"\b(a|one)\s+month", posted):
        return 30
    return None


# ---- stage 2: reading each offer ----

class _Progress:
    """Counts the offers read across all sites and says so every 10."""

    def __init__(self, total: int, label: str = ""):
        self.total = total
        self.done = 0
        self.label = label or _("lues")

    def step(self) -> None:
        with _print_lock:
            self.done += 1
            if self.done % 10 == 0 or self.done == self.total:
                print(f"  {self.done}/{self.total} {self.label}")
            if _progress_lines:
                print("@@ offer")


def _read_offers(jobs: list[Job], filters: Filters, progress: _Progress) -> list[tuple[Job, str]]:
    """Reads one site's offers, one after the other."""
    session = new_session()
    results = []
    for job in jobs:
        results.append((job, _rejection(session, job, filters)))
        progress.step()
    return results


def _rejection(session, job: Job, filters: Filters) -> str:
    """Reads the posting and fills in its details: why it is dropped ("langue", "salaire"...), or "" to keep it."""
    if not job.description:
        try:
            job.description = page_text(session, job.url)
        except Exception:
            job.experience = "page non lue"  # kept so you can judge it yourself
    text = f"{job.title} {job.description}"
    job.contract = job.contract or contract_type(job.title, job.description)
    job.work_mode = job.work_mode or work_mode(job.location, job.description)
    job.salary = job.salary or salary_range(job.description)
    job.skills = skills_found(text, filters.skills)
    if any(requires_language(job.title, job.description, language) for language in filters.languages):
        return "langue"
    if any(_has_whole_word(text, word) for word in filters.forbidden_words):
        return "mot interdit"
    if filters.required_words and job.description and not any(
            _has_whole_word(text, word) for word in filters.required_words):
        return "mot obligatoire absent"
    if job.contract and job.contract not in filters.contracts:
        return "contrat"
    if job.work_mode and job.work_mode not in filters.work_modes:
        return "mode de travail"
    if filters.min_salary and job.salary and job.salary[1] < filters.min_salary:
        return "salaire"
    if job.experience == "page non lue":
        return ""
    if any(_has_whole_word(job.title, word) for word in JUNIOR_WORDS):
        job.experience = "junior"
        return ""
    years = years_required(job.description)
    job.experience = "non précisé" if years is None else f"{years}+ ans"
    return "expérience" if years is not None and years > filters.max_years else ""


def _row(job: Job) -> dict:
    """The offer as a line of jobs.xlsx."""
    return {"Trouvée le": date.today().isoformat(), "Catégorie": job.category, "Score": len(job.skills),
            "Titre": job.title, "Entreprise": job.company, "Ville": job.location, "Publiée": job.posted,
            "Expérience": job.experience, "Contrat": job.contract, "Mode de travail": job.work_mode,
            "Salaire": salary_text(job.salary), "Compétences": ", ".join(job.skills), "Site": job.source,
            "Trouvée par": job.search, "Lien": job.url, "Statut": "", "Statut modifié le": "", "Notes": "",
            "En ligne": results_file.ONLINE, "Vérifiée le": date.today().isoformat(), "Description": job.description}


# ---- what is already known ----

def _drop_expired(rows: list[dict], keep_days: int) -> tuple[list[dict], int]:
    """Removes offers found more than keep_days ago, except those you wrote a Statut for."""
    if not keep_days:
        return rows, 0
    kept = []
    for row in rows:
        try:
            age = (date.today() - date.fromisoformat(row.get("Trouvée le", "")[:10])).days
        except ValueError:
            age = 0  # unreadable date: keep it
        if age <= keep_days or row.get("Statut", "").strip():
            kept.append(row)
    return kept, len(rows) - len(kept)


def _checked_links() -> set[str]:
    if not CHECKED_FILE.exists():
        return set()
    return {line.strip() for line in CHECKED_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}


def _job_agent_links(job_agent_folder: str) -> set[str]:
    """Offers already in Job Application Agent's tracker."""
    tracker = (APP_DIR / job_agent_folder / "applications" / "tracker.csv").resolve() if job_agent_folder else None
    if not tracker or not tracker.exists():
        return set()
    with tracker.open(encoding="utf-8-sig", newline="") as f:
        return {canonical_url(row["url"]) for row in csv.DictReader(f) if row.get("url")}


if __name__ == "__main__":
    sys.exit(main())
