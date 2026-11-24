"""Shared pieces for every source: the Job record, polite HTTP requests, text helpers."""
import random
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


@dataclass
class Job:
    source: str
    title: str
    company: str
    location: str
    url: str
    posted: str = ""  # ISO date (2026-10-27) when the site gives one, otherwise its own wording
    search: str = ""
    category: str = ""
    description: str = ""  # filled from the job page when the list doesn't give it
    experience: str = ""  # what the posting asks for, e.g. "2+ years"
    contract: str = ""  # "Temps plein", "Stage"... (settings.CONTRACTS), when known
    work_mode: str = ""  # "Sur place", "Hybride", "Télétravail" (settings.WORK_MODES), when known
    salary: tuple[int, int, str] | None = None  # (lowest, highest, currency) gross per month
    skills: list[str] = field(default_factory=list)  # skills from the settings found in the posting


@dataclass
class Settings:
    max_pages: int
    max_age_days: int
    remote_locations: list[str]
    careerfinders_categories: list[tuple[str, str]] = field(default_factory=list)  # (name, code)
    companies: list[dict] = field(default_factory=list)  # {"name", "platform", "id"}
    cities: list[str] = field(default_factory=list)


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    })
    return session


def fetch(session: requests.Session, url: str, params: dict | None = None,
          *, as_json: bool = False, post: dict | None = None, tries: int = 3):
    """GET a page (or POST the `post` JSON), waiting a little before each request so sites aren't hammered."""
    error = ""
    for attempt in range(tries):
        time.sleep(random.uniform(1.0, 2.0))
        try:
            if post is not None:
                response = session.post(url, params=params, json=post, timeout=25)
            else:
                response = session.get(url, params=params, timeout=25)
        except requests.RequestException as exc:
            error = str(exc)
            continue
        if response.status_code == 200:
            return response.json() if as_json else response.text
        error = f"HTTP {response.status_code}"
        if response.status_code in (429, 999):  # "too many requests": the site needs a real break
            time.sleep(30 * (attempt + 1))
            continue
        if response.status_code in (500, 502, 503, 504):
            time.sleep(5 * (attempt + 1))
            continue
        break
    raise RuntimeError(f"{urlsplit(url).netloc} did not answer ({error})")


def page_text(session: requests.Session, url: str) -> str:
    """The readable text of a job page, without menus, footers and lists of other jobs."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(fetch(session, url), "html.parser")
    for node in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        node.decompose()
    # other offers shown around the posting (Ergodotisi's jobs-card, CyprusJobs' v2-job-card-row...)
    for node in soup.select("[class*=related], [class*=similar], [class*=recommend], "
                            "[class*=jobs-card], [class*=job-card]"):
        node.decompose()
    return clean(soup.get_text(" "))


def clean(text: str | None) -> str:
    return " ".join(text.split()) if text else ""


def canonical_url(url: str) -> str:
    """One spelling per job, so the same offer is never saved twice."""
    match = re.search(r"linkedin\.com/jobs/view/(?:[^/?#]*-)?(\d+)", url)
    if match:
        return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme or "https", parts.netloc.lower(), parts.path, "", ""))


def has_word(text: str, word: str) -> bool:
    """True when a word starts in the text: "analyst" finds "Analysts" but "shop" skips "Workshop"."""
    return re.search(rf"\b{re.escape(word)}", text, re.IGNORECASE) is not None


def title_matches(title: str, search: str) -> bool:
    """True when every word of the search appears in the title."""
    return all(has_word(title, word) for word in search.split())


# What a job site shows once an offer is closed
_EXPIRED = re.compile(
    r"no longer (?:available|active|accepting|open|exists)|(?:job|position|vacancy|posting|offer|ad) "
    r"(?:has |is )?(?:expired|closed|been filled|been removed|not found)|this (?:job|position|vacancy) is closed"
    r"|applications? (?:are |is )?(?:now )?closed|job not found|page not found|404 not found"
    r"|η αγγελία έχει λήξει|δεν είναι πλέον διαθέσιμη", re.IGNORECASE)


def check_online(session: requests.Session, url: str) -> bool | None:
    """True while the offer is still published, False once removed or closed, None when the site can't tell."""
    from bs4 import BeautifulSoup

    time.sleep(random.uniform(1.0, 2.0))
    try:
        response = session.get(url, timeout=25)
    except requests.RequestException:
        return None
    if response.status_code in (404, 410):
        return False
    if response.status_code != 200:
        return None  # 403, 429, 5xx: blocked or busy, try again another day
    before, after = urlsplit(url).path.rstrip("/"), urlsplit(response.url).path.rstrip("/")
    if before != after and len(after) < len(before) and before.startswith(after):
        return False  # sent back to the list of offers: "/jobs/123-data-analyst" -> "/jobs"
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript", "nav", "footer", "aside"]):
        node.decompose()
    return not _EXPIRED.search(soup.get_text(" ")[:20000])
