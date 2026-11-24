"""The search settings, stored in settings.json and edited in the app window.

Standard library only: app.py imports it before the app's own packages are installed.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

# Where settings.json, results/ and .cache/ live: next to the code, or next to the .exe once built.
# RETRIEVE_JOB_HOME puts them somewhere else (the window test uses it, so it never touches your files).
APP_DIR = (Path(os.environ["RETRIEVE_JOB_HOME"]) if os.environ.get("RETRIEVE_JOB_HOME") else
           Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent)
SETTINGS_FILE = APP_DIR / "settings.json"
BROKEN_SETTINGS = APP_DIR / "settings.broken.json"  # a settings.json that could not be read, kept for you

# Every site the app can read, with the name shown in the window.
SITE_NAMES = {
    "ergodotisi": "Ergodotisi.com",
    "cyprusjobs": "CyprusJobs.com",
    "cypruswork": "CyprusWork.com",
    "fxcareer": "FxCareer.eu",
    "kariera": "Kariera.com.cy",
    "eures": "EURES (portail emploi de l'Union européenne)",
    "workable": "Workable (toutes les entreprises qui recrutent à Chypre avec Workable)",
    "djinni": "Djinni (tech : Chypre et télétravail ouvert à l'Europe)",
    "relocate": "Relocate.me (postes avec aide à la relocalisation à Chypre)",
    "careerfinders": "CareerFinders.com.cy (par catégories, à choisir ci-dessous)",
    "emeraldzebra": "EmeraldZebra.cy (fintech, tech, finance, iGaming : toutes ses offres)",
    "companies": "Pages carrières des entreprises suivies (onglet « Entreprises »)",
    "remoteok": "RemoteOK (télétravail)",
    "jobicy": "Jobicy (télétravail)",
    "remotive": "Remotive (télétravail)",
    "weworkremotely": "We Work Remotely (télétravail)",
    "himalayas": "Himalayas (télétravail ouvert à Chypre)",
}

# CareerFinders lists its offers by category: name shown on the site -> code in its links.
CAREERFINDERS_CATEGORIES = {
    "Accounting - Non-Qualified": "ACCA-NON", "Accounting - Part-Qualified": "ACCA/PQ",
    "Accounting - Qualified": "ACCA", "Administration/Secretarial": "ADMIN", "Audit": "AUDIT",
    "Banking/Finance": "Bank", "Compliance": "COMP", "Corporate/Fiduciary Services": "COR",
    "Customer Services": "CUSTOM", "Data Analysis": "DA", "Engineering & Construction": "ENGI",
    "FinTech": "FINTECH", "Forex": "FX", "Graphic Design": "GRAPH", "Health & Safety": "H&S",
    "Human Resources": "HR", "Information Technology (IT)": "IT", "Insurance": "INS", "Legal": "LEGAL",
    "Logistics/Purchasing": "LOGI", "Marketing/PR": "PR", "Oil & Gas": "OIL", "Online Gaming": "OG ",
    "Operations": "OPER", "Payment Service Providers (PSPs)": "PSPs", "Pharmaceutical": "PHARM",
    "Real Estate": "RE", "Recent Graduates": "REGRAD", "Risk": "Risk",
    "Sales/Business Development": "SALES", "Shipping": "SHIP", "Tax": "TAX", "Telecommunications": "TELECO",
}

# Hiring platforms whose job lists are public: name shown in the window -> code used by sources/companies.py.
COMPANY_PLATFORMS = {"Greenhouse": "greenhouse", "Lever": "lever", "Workable": "workable",
                     "SmartRecruiters": "smartrecruiters"}
CONTRACTS = ["Temps plein", "Temps partiel", "Stage", "Contrat / freelance"]
WORK_MODES = ["Sur place", "Hybride", "Télétravail"]

DEFAULTS = {
    # Job types, in order: when a title fits several, the first one wins.
    #   searches:    what is typed in each site's search box
    #   title_words: a job goes in the type when its title contains one of these words
    "categories": [
        {
            "name": "data",
            "searches": ["data analyst", "business intelligence", "reporting analyst", "business analyst"],
            "title_words": ["data", "analytics", "business intelligence", "bi analyst", "bi developer",
                            "power bi", "reporting analyst", "business analyst", "insights analyst"],
        },
        {
            "name": "dev",
            "searches": ["web developer", "frontend developer", "full stack developer", "junior developer"],
            "title_words": ["web developer", "web designer", "webmaster", "website", "developer", "frontend",
                            "front-end", "front end", "full stack", "fullstack", "full-stack", "javascript",
                            "react", "php", "wordpress", "software engineer"],
        },
        {
            "name": "french / sales / support",
            "searches": ["french", "retention", "sales", "customer support", "customer service"],
            "title_words": ["french", "francophone", "retention", "sales", "support", "customer",
                            "client success", "client relationship", "account manager"],
        },
    ],
    "max_experience_years": 3,
    "excluded_languages": ["greek"],
    "seniority_words": ["senior", "sr", "principal", "director", "head of", "chief", "vp", "expert",
                        "architect", "team lead", "tech lead", "technical lead", "lead developer",
                        "lead engineer", "lead analyst"],
    # With their suburbs, where many offices are ("Cyprus, Ypsonas", "Strovolos, Nicosia")
    "cities": ["nicosia", "lefkosia", "strovolos", "aglantzia", "engomi", "egkomi", "lakatamia", "latsia",
               "larnaca", "larnaka", "aradippou", "livadia", "oroklini", "dromolaxia", "pyla", "dali", "idalion",
               "limassol", "lemesos", "ypsonas", "germasogeia", "agios athanasios", "mesa geitonia", "polemidia"],
    # An offer whose location also names one of these places is for a job abroad ("Limassol, Dubai")
    "excluded_places": ["dubai", "uae", "united arab emirates", "yerevan", "armenia", "tbilisi", "georgia",
                        "latam", "mea", "apac", "israel", "tel aviv"],
    "max_age_days": 31,
    "keep_found_days": 31,  # offers found longer ago leave jobs.xlsx (unless you wrote a Statut); 0 = never
    "careerfinders_categories": [
        "Customer Services", "Data Analysis", "FinTech", "Forex", "Online Gaming", "Information Technology (IT)",
        "Shipping", "Payment Service Providers (PSPs)", "Recent Graduates", "Sales/Business Development",
    ],
    # Companies whose own careers page is read; id = the name in their careers-page link
    "companies": [
        {"name": "FxPro", "platform": "greenhouse", "id": "fxpro"},
        {"name": "Soft2Bet", "platform": "greenhouse", "id": "soft2bet"},
        {"name": "Wolt", "platform": "greenhouse", "id": "wolt"},
        {"name": "JetBrains", "platform": "greenhouse", "id": "jetbrains"},
        {"name": "Capital.com", "platform": "lever", "id": "capital"},
        {"name": "Easybrain", "platform": "lever", "id": "easybrain"},
        {"name": "Admirals", "platform": "workable", "id": "admirals"},
        {"name": "Playtech", "platform": "smartrecruiters", "id": "Playtech"},
        {"name": "Swissquote", "platform": "smartrecruiters", "id": "swissquote"},
    ],
    "companies_keep_all": False,  # True: also their offers that fit no job type, in "Entreprises suivies"
    "exclude_words": ["german", "italian", "spanish", "portuguese", "dutch", "russian", "polish", "lithuanian",
                      "czech", "hungarian", "romanian", "bulgarian", "turkish", "arabic", "hebrew", "korean",
                      "japanese", "chinese", "mandarin", "swedish", "norwegian", "danish", "finnish"],
    "excluded_companies": [],
    "required_words": [],   # the offer's text must contain at least one of these (empty = no condition)
    "forbidden_words": [],  # the offer is dropped when its text contains one of these
    # Each skill found in the offer adds 1 to its Score
    "skills": ["sql", "python", "excel", "power bi", "tableau", "looker", "google analytics", "javascript",
               "typescript", "react", "node", "html", "css", "php", "wordpress", "git", "crm", "salesforce",
               "hubspot", "french", "english"],
    "contracts": {name: True for name in CONTRACTS},
    "work_modes": {name: True for name in WORK_MODES},
    "min_salary": 0,  # € gross per month; offers that don't say are kept; 0 = no condition
    "remote_locations": ["anywhere", "worldwide", "europe", "emea", "eu", "cyprus", "remote"],
    "max_pages": 3,
    "job_agent_folder": "../job_agent",
    # Djinni and Himalayas are mostly fully remote offers (worldwide, Europe): ticked when you want those
    "sources": {name: name not in ("djinni", "himalayas") for name in SITE_NAMES},
    "check_online": True,  # each search checks that the offers already in the file are still online
    "backups_to_keep": 10,  # copies of jobs.xlsx made before each search, in results/backups; 0 = none
    "notify": True,
    "theme": "light",
    "text_size": "normal",  # small, normal, large, xlarge
    "density": "normal",  # height of the table rows: compact, normal, airy
    "language": "fr",  # "fr" or "en": the window, the search log and jobs.xlsx
}


# Defaults of older versions: a saved value still equal to one of them was never changed, so it gets the new default.
_OLD_DEFAULTS = {
    "cities": [["nicosia", "lefkosia", "larnaca", "larnaka", "pyla", "dali", "idalion", "limassol", "lemesos"]],
}


def load() -> dict:
    """The saved settings, with defaults filled in for anything missing."""
    settings = json.loads(json.dumps(DEFAULTS))  # deep copy
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(saved, dict):
                raise ValueError("not a dictionary")
        except (OSError, ValueError):  # damaged (edited by hand, disk full...): defaults, and a copy of it is kept
            try:
                shutil.copy2(SETTINGS_FILE, BROKEN_SETTINGS)
            except OSError:
                pass
            return settings
        settings.update({key: value for key, value in saved.items()
                         if key in DEFAULTS and value not in _OLD_DEFAULTS.get(key, [])})
        for key, names in (("sources", SITE_NAMES), ("contracts", CONTRACTS), ("work_modes", WORK_MODES)):
            settings[key] = {name: bool(saved.get(key, {}).get(name, DEFAULTS[key][name])) for name in names}
    return settings


def save(settings: dict) -> None:
    write_safely(SETTINGS_FILE, json.dumps(settings, indent=2, ensure_ascii=False))


def write_safely(path: Path, text: str) -> None:
    """Writes a text file without ever leaving it half written (if the PC stops in the middle, the old one stays)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".saving")
    temporary.write_text(text, encoding="utf-8")
    replace_file(temporary, path)


def replace_file(new: Path, old: Path) -> None:
    """Puts new in the place of old in one step. Retries a moment when the antivirus or the indexer holds old;
    raises PermissionError if it stays held (jobs.xlsx open in Excel)."""
    for attempt in range(6):
        try:
            os.replace(new, old)
            return
        except PermissionError:
            if attempt == 5:
                new.unlink(missing_ok=True)
                raise
            time.sleep(0.2)
